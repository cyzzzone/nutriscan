const API_URL = "http://127.0.0.1:8000/api/v1";
let ingredientesParaSalvar = [];

// 1. Navegação
function mudarTela(idTela) {
    document.querySelectorAll('.tela').forEach(tela => tela.classList.remove('ativa'));
    document.getElementById(idTela).classList.add('ativa');
    
    // Se clicar na geladeira, ela atualiza o Dashboard e a si mesma
    if(idTela === 'aba-geladeira') carregarDespensa();
}

// 2. Extração de Itens (Passo 1)
async function extrairItensDaNota() {
    const urlNota = document.getElementById('input-url').value;
    const statusText = document.getElementById('status-leitor');
    const areaSelecao = document.getElementById('area-selecao');
    const btnExtrair = document.getElementById('btn-extrair');

    if (!urlNota) return alert("Por favor, insira o link da nota.");

    statusText.innerText = "⏳ Lendo cupom fiscal na Sefaz...";
    btnExtrair.disabled = true;
    areaSelecao.style.display = "none";

    try {
        const resposta = await fetch(`${API_URL}/extrair-nota`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlNota })
        });

        const dados = await resposta.json();

        if (resposta.ok) {
            statusText.innerText = "✅ Leitura concluída!";
            const divCheckboxes = document.getElementById('lista-checkboxes');
            divCheckboxes.innerHTML = "";

            dados.itens_disponiveis.forEach((item, index) => {
                const div = document.createElement('div');
                div.className = "item-checkbox";
                div.innerHTML = `
                    <input type="checkbox" id="check-${index}" value="${item}" checked>
                    <label for="check-${index}">${item}</label>
                `;
                divCheckboxes.appendChild(div);
            });

            areaSelecao.style.display = "block";
            btnExtrair.innerText = "Carregar Novamente";
        } else {
            statusText.innerText = `❌ Erro: ${dados.detail}`;
        }
    } catch (erro) {
        statusText.innerText = "❌ Erro de conexão com o servidor Python.";
    } finally {
        btnExtrair.disabled = false;
    }
}

// 3. Análise da IA (Passo 2)
async function enviarSelecaoParaIA() {
    const statusText = document.getElementById('status-leitor');
    const areaSelecao = document.getElementById('area-selecao');

    const checkboxes = document.querySelectorAll('#lista-checkboxes input[type="checkbox"]:checked');
    const itensSelecionados = Array.from(checkboxes).map(cb => cb.value);

    if (itensSelecionados.length === 0) {
        return alert("Selecione pelo menos um item para analisar!");
    }

    statusText.innerText = "🧠 IA calculando validade e nutrição... Aguarde.";
    areaSelecao.style.display = "none"; 

    try {
        const resposta = await fetch(`${API_URL}/analisar-selecao`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ itens_selecionados: itensSelecionados })
        });

        const dados = await resposta.json();

        if (resposta.ok) {
            statusText.innerText = "✅ Salvo com sucesso!";
            
            // CARREGA A GELADEIRA, QUE VAI ATUALIZAR O DASHBOARD!
            carregarDespensa();
            
            const divDicas = document.getElementById('dicas-nutri');
            divDicas.innerHTML = `
                <div class="card-dica"><strong>Dica:</strong> ${dados.feedbacks.dica_positiva || "Análise concluída"}</div>
                <div class="card-dica alerta"><strong>Atenção:</strong> ${dados.feedbacks.alerta_melhoria || "Tudo certo!"}</div>
            `;

            document.getElementById('texto-dica-popup').innerText = "Itens guardados na despensa!";
            document.getElementById('popup-feedback').classList.add('popup-ativo');

            // --- NOVO: LIMPA A CAIXA DE TEXTO DA FEIRA LIVRE ---
            document.getElementById('input-texto-manual').value = "";

        } else {
            statusText.innerText = `❌ Erro na IA: ${dados.detail}`;
            areaSelecao.style.display = "block"; 
        }
    } catch (erro) {
        statusText.innerText = "❌ Erro ao enviar para a IA.";
        areaSelecao.style.display = "block";
    }
}

// 4. Atualizar o Dashboard (Chamado pela Geladeira)
// 4. Atualizar o Dashboard (Com Lógica Diária Real!)
async function atualizarDashboard() {
    try {
        // 1. Busca o consumo EXATO do dia de hoje no Python
        const respostaDiaria = await fetch(`${API_URL}/resumo-diario`);
        const dadosDiarios = await respostaDiaria.json();

        // 2. Atualiza o Gráfico de Água
        let aguaBebidaHoje = dadosDiarios.agua_hoje || 0;
        document.getElementById('valor-hidratacao').innerText = aguaBebidaHoje;
        
        let porcentagem = Math.min(Math.max((aguaBebidaHoje / 2000) * 100, 0), 100);
        document.getElementById('porcentagem-texto').innerText = `${Math.round(porcentagem)}%`;
        document.getElementById('grafico-circular').style.background = `conic-gradient(#006400 0% ${porcentagem}%, #e0e0e0 ${porcentagem}% 100%)`;

        // 3. Atualiza o Termômetro com o que ainda está na Geladeira
        let totalClasses = dadosDiarios.classificacoes_geladeira.length;
        let qtdInNatura = 0, qtdProcessado = 0, qtdUltra = 0;

        if (totalClasses > 0) {
            dadosDiarios.classificacoes_geladeira.forEach(classe => {
                let cl = classe ? classe.toLowerCase() : "";
                if (cl.includes("natura")) qtdInNatura++;
                else if (cl.includes("ultra")) qtdUltra++;
                else qtdProcessado++; 
            });

            document.getElementById('barra-in-natura').style.width = `${(qtdInNatura / totalClasses) * 100}%`;
            document.getElementById('barra-processado').style.width = `${(qtdProcessado / totalClasses) * 100}%`;
            document.getElementById('barra-ultra').style.width = `${(qtdUltra / totalClasses) * 100}%`;
        } else {
            document.getElementById('barra-in-natura').style.width = `0%`;
            document.getElementById('barra-processado').style.width = `0%`;
            document.getElementById('barra-ultra').style.width = `0%`;
        }

        // 4. Busca as validades (Olhando para a Despensa real)
        const respostaDespensa = await fetch(`${API_URL}/despensa`);
        const dadosDespensa = await respostaDespensa.json();
        
        const listaValidade = document.getElementById('lista-validade');
        listaValidade.innerHTML = ""; 
        ingredientesParaSalvar = [];

        dadosDespensa.detalhes_produtos.forEach(item => {
            let validadeNum = parseInt(item.validade_dias);
            if (!isNaN(validadeNum) && validadeNum > 0 && validadeNum < 30) {
                const li = document.createElement('li');
                let qtd = item.quantidade ? `${item.quantidade} ` : "";
                li.innerHTML = `<strong>${qtd}${item.nome_produto}</strong> - Vence em ${validadeNum} dias`;
                listaValidade.appendChild(li);
                ingredientesParaSalvar.push(item.nome_produto);
            }
        });

        const divDicas = document.getElementById('dicas-nutri'); // Pega a caixinha de dicas

        if (ingredientesParaSalvar.length > 0) {
            document.getElementById('btn-receita').style.display = "block";
            document.getElementById('box-receita').style.display = "none";
            
            // NOVO: DICA DINÂMICA BASEADA NAS VALIDADES!
            // Pega até os 3 primeiros itens que vão vencer para não poluir a tela
            let itensUrgentes = ingredientesParaSalvar.slice(0, 3).join(", ");
            
            divDicas.innerHTML = `
                <div class="card-dica alerta">
                    <strong>⏰ Risco de Desperdício:</strong> Priorize o consumo de <b>${itensUrgentes}</b>! Eles vão vencer em breve.
                </div>
                <div class="card-dica">
                    <strong>💡 Dica de Ouro:</strong> Clique no botão "O que cozinhar hoje?" logo acima e deixe a IA inventar uma receita com esses ingredientes para salvar o seu dinheiro.
                </div>
            `;
        } else {
            document.getElementById('btn-receita').style.display = "none";
            listaValidade.innerHTML = "<li>Nenhum item perecível com vencimento próximo.</li>";
            
            // NOVO: DICA POSITIVA QUANDO TUDO ESTÁ BEM
            divDicas.innerHTML = `
                <div class="card-dica" style="border-left-color: #28a745;">
                    <strong>✅ Despensa Segura:</strong> Você não tem nenhum alimento perto de estragar no momento. Belo planejamento de compras!
                </div>
            `;
        }

    } catch (erro) {
        console.error("Erro ao atualizar o Dashboard diário:", erro);
    }
}

// 5. Receita Anti-Desperdício
async function pedirReceita() {
    const btn = document.getElementById('btn-receita');
    const box = document.getElementById('box-receita');
    const texto = document.getElementById('texto-receita');

    btn.style.display = "none";
    box.style.display = "block";
    texto.innerText = "👨‍🍳 O Nutri está pensando em uma receita rápida...";

    try {
        const resposta = await fetch(`${API_URL}/receita-rapida`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ingredientes: ingredientesParaSalvar })
        });
        const dados = await resposta.json();
        if (resposta.ok) texto.innerHTML = `<strong>Receita Anti-Desperdício:</strong><br>${dados.receita}`;
        else texto.innerText = "Puxa, a IA não conseguiu pensar em uma receita agora.";
    } catch (erro) {
        texto.innerText = "Erro ao conectar com o chef IA.";
    }
}

// 6. Lista Inteligente
async function gerarLista() {
    const statusText = document.getElementById('status-lista');
    statusText.innerText = "⏳ A IA está analisando seu histórico...";
    document.getElementById('resultado-lista').style.display = "none";

    try {
        const resposta = await fetch(`${API_URL}/lista-inteligente`, { method: 'POST' });
        const dados = await resposta.json();

        if (resposta.ok) {
            statusText.innerText = "";
            document.getElementById('resultado-lista').style.display = "block";

            const listaBase = document.getElementById('itens-base');
            listaBase.innerHTML = "";
            dados.lista_base_recorrente.forEach(item => {
                const li = document.createElement('li');
                li.innerText = item;
                listaBase.appendChild(li);
            });

            document.getElementById('ia-item').innerText = dados.upgrade_ia.sugestao_item;
            document.getElementById('ia-justificativa').innerText = dados.upgrade_ia.justificativa;
        } else {
            statusText.innerText = `❌ Erro: ${dados.detail}`;
        }
    } catch (erro) {
        statusText.innerText = "❌ Erro de conexão com o servidor.";
    }
}

// 7. Geladeira CRUD e Sincronização
async function carregarDespensa() {
    const lista = document.getElementById('lista-despensa');
    lista.innerHTML = "<li>Carregando sua despensa...</li>";

    try {
        const resposta = await fetch(`${API_URL}/despensa`);
        const dados = await resposta.json();

        atualizarDashboard(dados);
        
        // NOVO: Atualiza os pontos junto com a geladeira!
        carregarGamificacao();

        lista.innerHTML = "";
        if (dados.detalhes_produtos.length === 0) {
            lista.innerHTML = "<li>Sua geladeira está vazia. Escaneie uma nota!</li>";
            return;
        }

        dados.detalhes_produtos.forEach(item => {
            const li = document.createElement('li');
            li.className = 'item-geladeira';
            let qtd = item.quantidade ? `${item.quantidade} ` : "";
            li.innerHTML = `
                <div class="item-info">
                    <strong>${qtd}- ${item.nome_produto}</strong> 
                    <small>Vence em ${item.validade_dias} dias</small>
                </div>
                <button class="btn-consumir" onclick="consumirItem(${item.id})">Consumir</button>
            `;
            lista.appendChild(li);
        });
    } catch (erro) {
        lista.innerHTML = "<li>Erro ao carregar banco de dados.</li>";
    }
}

async function consumirItem(id) {
    if (!confirm("Confirmar que utilizou este item? Ele sairá da sua geladeira e dos seus alertas!")) return;
    try {
        const resposta = await fetch(`${API_URL}/despensa/${id}/consumir`, { method: 'PUT' });
        if (resposta.ok) carregarDespensa(); 
    } catch (erro) {
        alert("Erro ao atualizar o banco de dados.");
    }
}

async function limparGeladeira() {
    if (!confirm("Tem certeza que deseja jogar tudo fora e esvaziar a geladeira?")) return;
    try {
        const resposta = await fetch(`${API_URL}/despensa`, { method: 'DELETE' });
        if (resposta.ok) {
            carregarDespensa(); 
            alert("Sua geladeira está limpinha!");
        }
    } catch (erro) {
        alert("Erro ao tentar limpar o banco de dados.");
    }
}

function fecharPopup() {
    document.getElementById('popup-feedback').classList.remove('popup-ativo');
    mudarTela('aba-inicio');
}

// Inicialização: Assim que abrir o App, carrega os dados reais da Base de Dados!
window.onload = carregarDespensa;

async function extrairItensManuais() {
    const textoManual = document.getElementById('input-texto-manual').value;
    const statusText = document.getElementById('status-leitor');
    const areaSelecao = document.getElementById('area-selecao');

    if (!textoManual.trim()) return alert("Por favor, descreva o que comprou.");

    statusText.innerText = "⏳ O Nutri está a ler o seu texto...";
    areaSelecao.style.display = "none";

    try {
        const resposta = await fetch(`${API_URL}/extrair-texto`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto: textoManual })
        });

        const dados = await resposta.json();

        if (resposta.ok && dados.itens_disponiveis.length > 0) {
            statusText.innerText = "✅ Itens identificados!";
            
            const divCheckboxes = document.getElementById('lista-checkboxes');
            divCheckboxes.innerHTML = "";

            dados.itens_disponiveis.forEach((item, index) => {
                const div = document.createElement('div');
                div.className = "item-checkbox";
                div.innerHTML = `
                    <input type="checkbox" id="check-manual-${index}" value="${item}" checked>
                    <label for="check-manual-${index}">${item}</label>
                `;
                divCheckboxes.appendChild(div);
            });

            areaSelecao.style.display = "block";
        } else {
            statusText.innerText = "❌ Não consegui identificar nenhum alimento.";
        }
    } catch (erro) {
        statusText.innerText = "❌ Erro ao conectar com a IA.";
    }
}

// =================================================================
// 8. Gamificação e Pontos
// =================================================================
async function carregarGamificacao() {
    try {
        const resposta = await fetch(`${API_URL}/gamificacao`);
        const dados = await resposta.json();
        
        if (resposta.ok) {
            document.getElementById('pontuacao-texto').innerText = dados.pontos;
            document.getElementById('nivel-texto').innerText = dados.nivel;
        }
    } catch (erro) {
        console.log("Erro ao carregar pontuação.");
    }
}