# Buscador de Imóveis

Ferramenta para enviar links de imóveis a clientes de forma rápida. Ela lê os imóveis do site da [Imobiliária Daros](https://imobiliariadaros.com.br/), guarda a lista (marcando o que é **novo**, o que teve **valor alterado** e o que foi **removido**) e oferece uma página de busca com botões para copiar o link ou uma mensagem pronta para WhatsApp.

Feita para quem **não é programador**: basta instalar o Python uma vez e dar duplo clique.

## 0. Baixar a ferramenta

Nesta página do GitHub, clique no botão verde **Code → Download ZIP**, extraia o ZIP em uma pasta do seu computador (ex.: Área de Trabalho) e siga os passos abaixo. Mantenha todos os arquivos juntos na mesma pasta.

## O que tem na pasta

| Arquivo | Para que serve |
|---|---|
| `atualizar.bat` (Windows) / `atualizar.command` (Mac) | Dá duplo clique para buscar os imóveis do site e atualizar a lista |
| `buscar.html` | A página de busca. Abre no navegador (Chrome, Edge, Safari…) |
| `imoveis.json` / `imoveis.js` | A lista de imóveis (gerada automaticamente – não edite) |
| `coletor.py` | O programa que lê o site (você não precisa abrir) |
| `coletor.log` | Histórico das atualizações (útil se algo der errado) |

## 1. Instalar o Python (só uma vez)

**Windows**
1. Entre em <https://www.python.org/downloads/> e baixe o instalador.
2. Abra o instalador e **marque a caixa "Add python.exe to PATH"** (embaixo, na primeira tela). Depois clique em *Install Now*.

**Mac**: baixe e instale o mesmo arquivo do site acima.

Pronto. As "dependências" (`requests` e `beautifulsoup4`) são instaladas **sozinhas** na primeira vez que você rodar a atualização.

## 2. Atualizar a lista de imóveis

- **Windows:** dê duplo clique em `atualizar.bat`.
- **Mac:** dê duplo clique em `atualizar.command`. Se o Mac reclamar de permissão, abra o Terminal uma vez e rode `chmod +x ` (com espaço no final), arraste o arquivo `atualizar.command` para a janela e aperte Enter. Na primeira vez, pode ser preciso clicar com o botão direito → *Abrir*.

Uma janela preta vai aparecer e mostrar o andamento. **Leva alguns minutos** (de propósito: o programa espera cerca de 1 segundo entre cada página para não sobrecarregar o site). Quando aparecer *"PRONTO!"*, pode fechar.

Se a atualização falhar (sem internet, site fora do ar…), a lista anterior **continua intacta** e o erro fica registrado em `coletor.log`.

### O que significam as marcações
- **Novo** – imóvel que apareceu desde a última atualização.
- **Valor alterado** – o preço mudou; a página mostra o valor antigo riscado e se subiu (▲) ou desceu (▼).
- **Removido** – saiu do site (provavelmente vendido). Fica visível só se você escolher "Removidos" no filtro *Situação*.

As marcações "Novo" e "Valor alterado" ficam por **7 dias**, assim você não perde nada se pular um dia. (Para mudar, altere `DIAS_DESTAQUE` no início do `coletor.py`.)

## 3. Abrir a página de busca

Dê duplo clique em `buscar.html`. Ela abre no navegador, **sem internet e sem instalar nada** (os dados vêm do arquivo `imoveis.js` que fica na mesma pasta – por isso mantenha os arquivos juntos).

- **Venda ou Locação:** os botões no topo (**Todos / Venda / Locação**) separam os imóveis, mostram quantos há em cada grupo e a página lembra a sua última escolha. Valores de locação aparecem como "R$ 600,00/mês" (inclusive na mensagem de WhatsApp). Os filtros de tipo e cidade se ajustam à aba escolhida.
- **Busca:** digite rua, bairro, título ou código. Acentos e maiúsculas não importam ("maringa" acha "Maringá").
- **Filtros:** valor mínimo/máximo, tipo, cidade, quartos e situação.
- **Copiar link** e **Copiar mensagem WhatsApp** em cada imóvel. Depois é só colar no WhatsApp.
- **Vários imóveis:** marque a caixinha de cada um (ou *Selecionar todos os resultados*). Aparece uma barra embaixo com **Copiar mensagem com todos**.

No celular, copie a pasta para o aparelho ou use o computador para montar a mensagem e envie. (A página funciona em celular, mas as atualizações são feitas no computador.)

## 4. Atualizar automaticamente todo dia de manhã

### Windows (Agendador de Tarefas)
1. Aperte a tecla **Windows**, digite **Agendador de Tarefas** e abra.
2. À direita, clique em **Criar Tarefa Básica…**
3. Nome: `Atualizar imóveis Daros` → Avançar.
4. Gatilho: **Diariamente** → escolha o horário (ex.: 07:30) → Avançar.
5. Ação: **Iniciar um programa** → em *Programa/script* clique em *Procurar* e escolha o `atualizar.bat`. Em **Adicione argumentos** escreva `auto` (assim a janela fecha sozinha no final). Em **Iniciar em** coloque o caminho da pasta (ex.: `C:\Users\Voce\Desktop\imoveis-daros`).
6. Concluir. Se o computador estiver desligado no horário, nas *Propriedades* da tarefa → aba *Configurações* marque **"Executar a tarefa o mais cedo possível após uma inicialização agendada ter sido perdida"**.

Alternativa em uma linha (no Prompt de Comando, ajuste o caminho):
```
schtasks /Create /SC DAILY /ST 07:30 /TN "Atualizar imoveis Daros" /TR "\"C:\CAMINHO\DA\PASTA\atualizar.bat\" auto"
```

### Mac (agendamento com cron)
1. Abra o **Terminal** e digite `crontab -e`.
2. Adicione a linha abaixo (ajuste o caminho) e salve:
```
30 7 * * * cd /Users/voce/imoveis-daros && /usr/bin/python3 coletor.py
```
(Todo dia às 07:30. O Mac precisa estar ligado nesse horário.)

## Problemas comuns

- **"Python não foi encontrado"** – refaça o passo 1 e lembre-se de marcar *Add python.exe to PATH*; depois feche e abra a janela.
- **A página mostra "Não encontrei a lista de imóveis"** – rode a atualização ao menos uma vez e mantenha `buscar.html` e `imoveis.js` na mesma pasta.
- **Quantidade de imóveis menor que o esperado** – veja `coletor.log`; se muitas páginas falharem (mais de 30%), o programa se recusa a trocar a lista.
- **O site mudou de layout** – o programa avisa no log ("layout mudou?"). Nesse caso é preciso ajustar o `coletor.py`.

## Como funciona (para curiosos)

O programa lê os imóveis **à venda** pelo `sitemap.xml` oficial do site (a lista de páginas que o próprio site publica para o Google) e os imóveis **para locação** pela listagem paginada do site (`/imoveis/locacao`), pois a locação não consta no sitemap. Confere ainda se a quantidade lida bate com a que o site informa. Depois visita a página de cada imóvel para extrair código, tipo, endereço, bairro, cidade, valor, quartos e área. Depois compara com a lista anterior para marcar novos, alterados e removidos. O site não oferece feed XML nem API pública; o sitemap é mais confiável que percorrer as páginas de listagem, que carregam a paginação por JavaScript.
