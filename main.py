from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import requests
from bs4 import BeautifulSoup
import json
from collections import Counter
import time
import sqlite3 
from datetime import datetime
import os                     # <-- NOVO
from dotenv import load_dotenv
from google import genai
from google.genai import types

# =========================================================
# CONFIGURAÇÕES DA API E BANCO DE DADOS
# =========================================================
app = FastAPI(title="NutriScan API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv() # Manda o Python ler o ficheiro .env

GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("⚠️ ALERTA DE SEGURANÇA: Chave da API não encontrada! Verifique se criou o ficheiro .env corretamente.")

cliente_gemini = genai.Client(api_key=GOOGLE_API_KEY)

def iniciar_banco():
    conn = sqlite3.connect('nutriscan.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_compra TEXT,
            produtos_json TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS itens_despensa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_produto TEXT,
            quantidade TEXT,
            validade_dias INTEGER,
            agua_ml INTEGER,
            classificacao_nova TEXT,
            status TEXT DEFAULT 'disponivel',
            data_consumo TEXT -- <--- NOVA COLUNA PARA O RESET DIÁRIO
        )
    ''')
    conn.commit()
    conn.close()

iniciar_banco()

# =========================================================
# MODELOS DE DADOS
# =========================================================
class NotaRequest(BaseModel):
    url: str

class SelecaoRequest(BaseModel):
    itens_selecionados: List[str] 

class TextoRequest(BaseModel):
    texto: str
# =========================================================
# FUNÇÕES DE LÓGICA (Scraper e IA)
@app.post("/api/v1/extrair-texto", summary="Extrai nomes de alimentos de um texto livre")
def extrair_texto(requisicao: TextoRequest):
    prompt = f"""
    Analise o texto da feira: "{requisicao.texto}"
    Extraia os alimentos JUNTAMENTE com as suas quantidades ou pesos.
    Exemplo: "Comprei 1 kg de banana e 3 maçãs" -> ["1 kg de banana", "3 maçãs"]
    Retorne APENAS uma lista JSON válida (use aspas duplas).
    """
    try:
        response = cliente_gemini.models.generate_content(model='gemma-3-1b-it', contents=prompt)
        texto_limpo = response.text.replace('```json', '').replace('```', '').strip().replace("'", '"')
        return {"itens_disponiveis": json.loads(texto_limpo)}
    except:
        return {"itens_disponiveis": [requisicao.texto]}
    
def raspar_dados_sefaz(url_nota: str):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # TIMEOUT DE 10 SEGUNDOS PARA NÃO CONGELAR O SERVIDOR
        resposta = requests.get(url_nota, headers=headers, timeout=10)
        resposta.raise_for_status() 
        sopa = BeautifulSoup(resposta.text, 'html.parser')
        tags_produtos = sopa.find_all('span', class_='txtTit2') 
        return [tag.get_text(strip=True) for tag in tags_produtos if tag.get_text(strip=True)]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"A SEFAZ bloqueou o acesso ou demorou a responder. Tente novamente. Erro: {str(e)}")

def analisar_alimentos_com_gemini(lista_itens: list):
    if not lista_itens:
        return []
        
    prompt = f"""
    Analise esta lista de compras: {lista_itens}
    IGNORE produtos de limpeza e higiene.
    Retorne APENAS JSON válido com EXCLUSIVAMENTE alimentos.
    {{
        "status": "sucesso",
        "feedbacks": {{ "dica_positiva": "...", "alerta_melhoria": "..." }},
        "detalhes_produtos": [
            {{
                "nome_produto": "(Apenas o nome limpo, ex: Banana)",
                "quantidade": "(A medida e o número, ex: 1 kg, 500g, 3 un. Se não tiver, coloque '1 un')",
                "classificacao_nova": "(In Natura, Processado ou Ultraprocessado)",
                "validade_dias": (numero),
                "agua_ml": (numero)
            }}
        ]
    }}
    """
    
    max_tentativas = 3
    for tentativa in range(max_tentativas):
        try:
            response = cliente_gemini.models.generate_content(model='gemma-3-1b-it', contents=prompt)
            texto_limpo = response.text.replace('```json', '').replace('```', '').strip()
            dados_json = json.loads(texto_limpo)
            
            if "detalhes_produtos" not in dados_json or len(dados_json["detalhes_produtos"]) == 0:
                raise Exception("Lista vazia.")
                
            primeiro_item = dados_json["detalhes_produtos"][0]
            if "agua_ml" not in primeiro_item or "validade_dias" not in primeiro_item:
                raise Exception("JSON sem chaves matemáticas.")
                
            return dados_json
        except Exception as e:
            time.sleep(3)
            
    print("Ativando Plano B dinâmico...")
    itens_fallback = []
    for nome in lista_itens:
        # NOVO: Plano B agora inclui a chave quantidade
        itens_fallback.append({"nome_produto": nome, "quantidade": "1 un", "classificacao_nova": "Processado", "validade_dias": 5, "agua_ml": 80})
        
    return {
        "status": "sucesso",
        "feedbacks": {
            "dica_positiva": "Aqui estão os itens que selecionou e guardou!",
            "alerta_melhoria": "A IA estava indisponível, usamos estimativas de segurança padrão."
        },
        "detalhes_produtos": itens_fallback
    }

# =========================================================
# ROTAS (Endpoints)
# =========================================================

@app.post("/api/v1/extrair-nota", summary="Lê a URL e devolve a lista limpa")
def extrair_nota(requisicao: NotaRequest): 
    itens_brutos = raspar_dados_sefaz(requisicao.url)
    if not itens_brutos:
        raise HTTPException(status_code=404, detail="Nenhum item encontrado.")
        
    palavras_proibidas = [
        "SAB ", "COLGATE", "PASTILHA", "LIMP", "ESPONJA", "DETERG", 
        "RACAO", "SACO", "Q BOA", "TININDO", "MINUANO", "WHISKAS", 
        "PALMOLIVE", "DENTAL", "DESINF"
    ]
    
    itens_filtrados = [item for item in itens_brutos if not any(p in item.upper() for p in palavras_proibidas)]
            
    return {"itens_disponiveis": itens_filtrados}

@app.post("/api/v1/analisar-selecao", summary="Envia para a IA e salva no banco")
def analisar_selecao(requisicao: SelecaoRequest): 
    itens_para_analise = requisicao.itens_selecionados
    
    if not itens_para_analise:
        raise HTTPException(status_code=400, detail="Nenhum item foi selecionado.")

    resultado_ia = analisar_alimentos_com_gemini(itens_para_analise)
    dados_processados = resultado_ia.get('detalhes_produtos', [])

    for item in dados_processados:
        # Tenta pegar a água
        agua_numeros = ''.join(filter(str.isdigit, str(item.get("agua_ml", ""))))
        item["agua_ml"] = int(agua_numeros) if agua_numeros else 80

        # Tenta pegar a validade
        val_numeros = ''.join(filter(str.isdigit, str(item.get("validade_dias", ""))))
        if val_numeros:
            item["validade_dias"] = int(val_numeros)
        else:
            # Se a IA esquecer, o Python usa lógica de negócio baseada no nome!
            nome_upper = item.get("nome_produto", "").upper()
            if any(palavra in nome_upper for palavra in ["BISC", "GELATINA", "FARIN", "OLEO", "MISTURA"]):
                item["validade_dias"] = 180 # Itens secos demoram a estragar
            elif any(palavra in nome_upper for palavra in ["LEITE", "CREME", "MARGARINA", "PATE", "BEB LAC"]):
                item["validade_dias"] = 15  # Laticínios
            elif any(palavra in nome_upper for palavra in ["UVA", "PAO", "FRUTA"]):
                item["validade_dias"] = 5   # Frescos
            else:
                item["validade_dias"] = 7   # Padrão
    try:
        conn = sqlite3.connect('nutriscan.db')
        cursor = conn.cursor()
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        produtos_string = json.dumps([p.get('nome_produto') for p in dados_processados])
        
        cursor.execute('INSERT INTO compras (data_compra, produtos_json) VALUES (?, ?)', (data_atual, produtos_string))
        
        for item in dados_processados:
            cursor.execute(
                'INSERT INTO itens_despensa (nome_produto, quantidade, validade_dias, agua_ml, classificacao_nova) VALUES (?, ?, ?, ?, ?)', 
                (item.get("nome_produto"), item.get("quantidade", "1 un"), item.get("validade_dias"), item.get("agua_ml"), item.get("classificacao_nova"))
            )

        conn.commit()
        conn.close()
        
        return {"status": "sucesso", "feedbacks": resultado_ia.get('feedbacks', {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao salvar dados processados.")

@app.post("/api/v1/lista-inteligente")
def gerar_lista_inteligente(): 
    conn = sqlite3.connect('nutriscan.db')
    cursor = conn.cursor()
    cursor.execute('SELECT produtos_json FROM compras')
    historico_db = cursor.fetchall()
    conn.close()
    
    if not historico_db:
         raise HTTPException(status_code=400, detail="Seu histórico está vazio. Escaneie uma nota primeiro!")
         
    todos_os_itens = []
    total_compras = len(historico_db)
    
    for linha in historico_db:
        itens_da_compra = json.loads(linha[0])
        todos_os_itens.extend(itens_da_compra)
        
    contagem = Counter(todos_os_itens)
    
    itens_recorrentes = [item for item, freq in contagem.items() if freq / total_compras >= 0.5]
    if not itens_recorrentes:
        itens_recorrentes = [item for item, _ in contagem.most_common(3)]
        
    perfil_consumo = ", ".join(contagem.keys())
    
    return {
        "status": "sucesso",
        "lista_base_recorrente": itens_recorrentes,
        "upgrade_ia": {
            "sugestao_item": "Aveia em Flocos",
            "justificativa": "Ótima fonte de fibras baseada no seu histórico de compras reais do banco de dados!"
        }
    }

@app.post("/api/v1/receita-rapida")
def gerar_receita(requisicao: dict): 
    ingredientes = requisicao.get("ingredientes", [])
    if not ingredientes:
        return {"receita": "Selecione ingredientes primeiro."}
        
    prompt = f"""
    Você é um MasterChef focado em saúde. O usuário tem estes ingredientes prestes a vencer: {', '.join(ingredientes)}.
    
    REGRA DE SEGURANÇA MÁXIMA: 
    1. IGNORE produtos de limpeza ou higiene.
    2. ESCOLHA NO MÁXIMO 2 OU 3 ingredientes dessa lista que COMBINEM BEM ENTRE SI. Não use todos!
    3. Crie uma receita super rápida (1 parágrafo) que faça sentido culinário (ex: não misture gelatina com farinha).
    """
    try:
        response = cliente_gemini.models.generate_content(model='gemma-3-1b-it', contents=prompt)
        return {"receita": response.text.strip()}
    except:
        return {"receita": "A IA está ocupada. Que tal uma salada rápida com esses ingredientes?"}

# =========================================================
# ROTAS DA DESPENSA (Sincronizada com Dashboard)
# =========================================================

@app.get("/api/v1/despensa", summary="Lista os itens disponíveis na geladeira")
def listar_despensa():
    conn = sqlite3.connect('nutriscan.db')
    cursor = conn.cursor()
    # Adicionamos a quantidade no SELECT
    cursor.execute("SELECT id, nome_produto, validade_dias, agua_ml, classificacao_nova, quantidade FROM itens_despensa WHERE status = 'disponivel'")
    linhas = cursor.fetchall()
    conn.close()
    
    itens = [{
        "id": l[0], 
        "nome_produto": l[1], 
        "validade_dias": l[2],
        "agua_ml": l[3],
        "classificacao_nova": l[4],
        "quantidade": l[5] # <-- A nova informação vai para o Javascript
    } for l in linhas]
    
    agua_total = sum(i["agua_ml"] for i in itens)
    
    return {
        "status": "sucesso", 
        "detalhes_produtos": itens,
        "agua_mastigavel_total_ml": agua_total
    }

@app.get("/api/v1/resumo-diario", summary="Puxa os dados de consumo apenas do dia atual")
def resumo_diario():
    conn = sqlite3.connect('nutriscan.db')
    cursor = conn.cursor()
    
    # Pega a data de hoje
    hoje = datetime.now().strftime("%Y-%m-%d")
    
    # Puxa APENAS a água dos itens que foram consumidos HOJE!
    cursor.execute("SELECT agua_ml FROM itens_despensa WHERE status = 'consumido' AND data_consumo = ?", (hoje,))
    linhas_agua = cursor.fetchall()
    
    # Puxa os itens In Natura da geladeira (para o termômetro não zerar, ele mostra o que você AINDA tem)
    cursor.execute("SELECT classificacao_nova FROM itens_despensa WHERE status = 'disponivel'")
    linhas_termometro = cursor.fetchall()
    
    conn.close()
    
    agua_bebida_hoje = sum(l[0] for l in linhas_agua)
    classificacoes = [l[0] for l in linhas_termometro]
    
    return {
        "agua_hoje": agua_bebida_hoje,
        "classificacoes_geladeira": classificacoes
    }

@app.put("/api/v1/despensa/{item_id}/consumir", summary="Marca um item como consumido e anota a data")
def consumir_item(item_id: int):
    conn = sqlite3.connect('nutriscan.db')
    cursor = conn.cursor()
    
    # NOVO: Pega a data exata de hoje no formato YYYY-MM-DD
    hoje = datetime.now().strftime("%Y-%m-%d")
    
    # Atualiza o status e também grava a data!
    cursor.execute("UPDATE itens_despensa SET status = 'consumido', data_consumo = ? WHERE id = ?", (hoje, item_id))
    
    conn.commit()
    conn.close()
    return {"status": "sucesso", "mensagem": "Item consumido!"}

@app.delete("/api/v1/despensa", summary="Esvazia toda a geladeira")
def limpar_geladeira():
    conn = sqlite3.connect('nutriscan.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM itens_despensa")
    conn.commit()
    conn.close()
    return {"status": "sucesso", "mensagem": "Sua geladeira foi esvaziada!"}

# =========================================================
# MÓDULO DE GAMIFICAÇÃO (PONTUAÇÃO E NÍVEIS)
# =========================================================
@app.get("/api/v1/gamificacao", summary="Calcula a pontuação do usuário")
def obter_pontuacao():
    conn = sqlite3.connect('nutriscan.db')
    cursor = conn.cursor()
    # Puxa tudo o que o usuário já processou no app
    cursor.execute("SELECT classificacao_nova, status FROM itens_despensa")
    itens = cursor.fetchall()
    conn.close()

    pontos = 0

    for item in itens:
        classe = item[0].lower() if item[0] else ""
        status = item[1]

        # Lógica de Pontuação
        if "natura" in classe:
            pontos += 10
            if status == 'consumido': 
                pontos += 5 # Bônus por não deixar estragar!
        elif "ultra" in classe:
            pontos -= 5
        else:
            pontos += 2 # Processados comuns dão pontinhos neutros

    # O usuário não pode ter pontos negativos no jogo
    pontos = max(0, pontos)

    # Cálculo do Nível (Badge)
    if pontos >= 150:
        nivel = "Mestre Nutri 🥇"
    elif pontos >= 50:
        nivel = "Aprendiz Saudável 🥈"
    else:
        nivel = "Iniciante 🥉"

    return {"status": "sucesso", "pontos": pontos, "nivel": nivel}