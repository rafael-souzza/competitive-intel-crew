import os
import time
import requests
from dotenv import load_dotenv
from crewai import Agent, Task

load_dotenv()

# ──────────────────────────────────────────────
# GEOLOCALIZAÇÃO (Nominatim + Overpass)
# ──────────────────────────────────────────────

def geocode(location: str) -> dict:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": location, "format": "json", "limit": 1}
    headers = {"User-Agent": "CompetitiveIntelCrew/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        if data:
            return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"]), "display_name": data[0]["display_name"]}
    except Exception:
        pass
    return {}

def search_local_competitors(lat: float, lon: float, niche: str, radius: int = 3000) -> list:
    tag_map = {
        "academia": '["leisure"="fitness_centre"]',
        "restaurante": '["amenity"="restaurant"]',
        "padaria": '["shop"="bakery"]',
        "farmacia": '["amenity"="pharmacy"]',
        "clinica": '["amenity"="clinic"]',
        "escola": '["amenity"="school"]',
    }
    tag = '["leisure"="fitness_centre"]'
    for key, value in tag_map.items():
        if key in niche.lower():
            tag = value
            break

    query = f'[out:json];node{tag}(around:{radius},{lat},{lon});out body 10;'
    try:
        resp = requests.post(
            "https://overpass.kumi.systems/api/interpreter",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"data={requests.utils.quote(query)}",
            timeout=5
        )
        if resp.status_code != 200:
            return []
        elements = resp.json().get("elements", [])
    except Exception:
        return []

    results = []
    for el in elements:
        name = el.get("tags", {}).get("name", "Sem nome")
        street = el.get("tags", {}).get("addr:street", "")
        phone = el.get("tags", {}).get("phone", "")
        website = el.get("tags", {}).get("website", "")
        results.append(f"{name} — {street}, telefone: {phone or 'não disponível'}, site: {website or 'não disponível'}")
    return results

def search_news(niche: str, location: str = "Brasil") -> list:
    """Busca notícias recentes via NewsAPI."""
    api_key = os.getenv("NEWSAPI_KEY", "")
    if not api_key:
        return []
    query = f"{niche} {location}" if location else niche
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "pt",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "apiKey": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") != "ok":
            return []
        articles = data.get("articles", [])
        results = []
        for a in articles:
            title = a.get("title", "Sem título")
            source = a.get("source", {}).get("name", "Fonte desconhecida")
            date = a.get("publishedAt", "")[:10]
            results.append(f"{title} — {source} ({date})")
        return results
    except Exception:
        return []

# ──────────────────────────────────────────────
# AGENTES
# ──────────────────────────────────────────────

trends_agent = Agent(
    role="Analista de Tendências de Mercado",
    goal="Identificar tendências de consumo e comportamento no nicho e localização informados, com base em dados objetivos.",
    backstory="Analista de mercado com formação em pesquisa de consumo. Utiliza dados públicos para embasar análises setoriais.",
    allow_delegation=False,
    verbose=False,
    llm="groq/llama-3.1-8b-instant",
)

competitors_agent = Agent(
    role="Analista de Inteligência Competitiva",
    goal="Mapear concorrentes diretos na região informada e analisar posicionamento, serviços e diferenciais.",
    backstory="Especialista em análise competitiva local. Foco em identificar players regionais e suas estratégias.",
    allow_delegation=False,
    verbose=False,
    llm="groq/llama-3.1-8b-instant",
)

content_agent = Agent(
    role="Estrategista de Conteúdo Digital",
    goal="Desenvolver recomendações de conteúdo para o negócio com base no nicho, localização e dados coletados.",
    backstory="Planejador de conteúdo com experiência em marketing digital. Foco em estratégias orgânicas e conversão.",
    allow_delegation=False,
    verbose=False,
    llm="groq/llama-3.1-8b-instant",
)

insights_agent = Agent(
    role="Consultor de Estratégia Empresarial",
    goal="Consolidar as análises em um relatório executivo com recomendações acionáveis e baseadas nos dados.",
    backstory="Consultor com experiência em estratégia competitiva. Foco em planos de ação realistas e mensuráveis.",
    allow_delegation=False,
    verbose=False,
    llm="groq/llama-3.1-8b-instant",
)

# ──────────────────────────────────────────────
# EXECUÇÃO
# ──────────────────────────────────────────────

def run_analysis(niche: str, location: str = ""):
    geo = {}
    competitors_list = []
    if location:
        geo = geocode(location)
        if geo:
            competitors_list = search_local_competitors(geo["lat"], geo["lon"], niche)

    competitors_text = "\n".join(competitors_list) if competitors_list else "Não foram encontrados concorrentes geolocalizados. Realize uma análise geral do nicho."

    news_list = search_news(niche, location)
    news_text = "\n".join(news_list) if news_list else "Nenhuma notícia recente encontrada."

    # ── 1. TENDÊNCIAS ──
    trends_prompt = f"""# CONTEXTO
Você é um analista de inteligência de mercado sênior contratado por uma empresa que atua ou deseja atuar no nicho '{niche}' na região de '{location or 'Brasil'}'. Seu relatório será lido por diretores e gerentes que tomarão decisões estratégicas com base na sua análise. O objetivo é identificar tendências de consumo e comportamento que afetam este setor na região especificada.

# PERSONA
Nome: Dr. Ricardo Viana
Formação: Doutor em Economia pela FGV, 15 anos como analista setorial no IBGE e consultor do Sebrae.
Estilo: Escrita técnica, objetiva, com embasamento em dados. Não faz especulações sem fundamento. Prefere apontar limitações da análise a fazer afirmações imprecisas.
Tom: Formal, analítico, imparcial. Não utiliza linguagem promocional ou motivacional.

# REGRAS ABSOLUTAS
1. NÃO utilize adjetivos como: incrível, revolucionário, explosivo, imperdível, extraordinário.
2. NÃO utilize frases de chamada como: "prepare-se para", "é hora de", "não fique para trás", "aproveite agora".
3. NÃO utilize emojis, hashtags ou markdown decorativo.
4. NÃO invente dados. Se não houver fonte disponível, indique: "Não foram encontrados dados públicos sobre este aspecto".
5. NÃO recomende ações. Sua função é apenas analisar tendências, não sugerir o que fazer com elas.
6. MANTENHA cada parágrafo com no máximo 4 linhas.
7. ESCREVA em português formal brasileiro.

# CRITÉRIOS DE ANÁLISE
Para cada tendência:
- Descrição: O que está acontecendo? Qual comportamento ou mudança foi observada?
- Causa provável: Que fator econômico, social ou tecnológico está impulsionando?
- Público impactado: Perfil demográfico (idade, renda, gênero, localização).
- Horizonte temporal: Curto prazo (meses), médio prazo (1-2 anos) ou estrutural (longo prazo)?
- Intensidade regional: Global, nacional ou específica da região?
- Sazonalidade: Há variação sazonal relevante?
- Fonte ou evidência: Cite fonte setorial se disponível. Se não houver, indique.

# FORMATO DE SAÍDA OBRIGATÓRIO
TENDÊNCIA 1: [Título descritivo e específico]
Descrição: [2-3 frases objetivas]
Causa provável: [1-2 frases]
Público impactado: [perfil demográfico]
Horizonte: [curto/médio/longo prazo]
Intensidade regional: [global/nacional/regional — justifique]
Sazonalidade: [sim/não — explique se sim]
Fonte: [fonte ou "Não foram encontrados dados públicos"]

TENDÊNCIA 2: [Título]
[...]

# INPUT
Nicho: {niche}
Localização: {location or 'Brasil'}
Notícias recentes do setor: {news_text}
Data da análise: {time.strftime('%d/%m/%Y')}

# OUTPUT
Entregue exclusivamente o relatório no formato especificado, sem introduções, resumos ou comentários adicionais."""

    t1 = Task(description=trends_prompt, expected_output="Relatório de tendências.", agent=trends_agent)
    r1 = t1.execute_sync(agent=trends_agent)
    time.sleep(10)

    # ── 2. CONCORRENTES ──
    competitors_prompt = f"""# CONTEXTO
Você é um analista de inteligência competitiva contratado por uma empresa que atua ou deseja atuar no nicho '{niche}' na região de '{location or 'Brasil'}'. Sua análise será utilizada pela diretoria para definir posicionamento de mercado e estratégia de entrada ou expansão.

# PERSONA
Nome: Dra. Mariana Campos
Formação: Mestre em Administração pela USP, 12 anos como analista de inteligência de mercado no Itaú e Bain & Company.
Estilo: Analítica, detalhista, baseada em evidências. Quando não há informação suficiente, sinaliza a limitação.
Tom: Formal, consultivo, imparcial. Trata concorrentes com respeito profissional.

# REGRAS ABSOLUTAS
1. NÃO utilize adjetivos subjetivos como: melhor, pior, fraco, ultrapassado.
2. NÃO faça juízos de valor sobre concorrentes. Descreva fatos e dados.
3. NÃO recomende ações diretas. Sua função é analisar, não decidir.
4. NÃO invente nomes, preços ou serviços. Se a informação não existir, indique "Dado não disponível".
5. NÃO utilize emojis, hashtags ou linguagem promocional.
6. MANTENHA cada parágrafo com no máximo 4 linhas.
7. ESCREVA em português formal brasileiro.
8. CITE fontes quando disponíveis.

# CRITÉRIOS DE ANÁLISE
Para cada concorrente:
- Nome e presença: Nome, tempo estimado de atuação, presença digital.
- Porte e estrutura: Pequeno, médio ou grande porte.
- Serviços oferecidos: Lista objetiva.
- Faixa de preço: Preço médio ou faixa observada.
- Público-alvo: Perfil demográfico e socioeconômico.
- Diferenciais declarados: O que o concorrente afirma ser seu diferencial.
- Pontos de atenção: Aspectos relevantes ou lacunas identificadas.

# FORMATO DE SAÍDA OBRIGATÓRIO
## Panorama do Mercado Local
[2-3 frases sobre o cenário competitivo]

## Concorrentes Mapeados
### Concorrente 1: [Nome]
- Porte: [pequeno/médio/grande]
- Serviços: [lista]
- Faixa de preço: [valor]
- Público-alvo: [perfil]
- Diferenciais declarados: [lista]
- Pontos de atenção: [observações]

### Concorrente 2: [Nome]
[...]

## Análise de Lacunas e Oportunidades
- Lacuna 1: [serviço ou público não atendido]
- Lacuna 2: [serviço ou público não atendido]
- Oportunidade 1: [diferencial pouco explorado]
- Oportunidade 2: [diferencial pouco explorado]

## Concorrentes Indiretos ou Substitutos
[Lista breve]

# INPUT
Nicho: {niche}
Localização: {location or 'Brasil'}
Concorrentes identificados via geolocalização: {competitors_text}
Data da análise: {time.strftime('%d/%m/%Y')}

# OUTPUT
Entregue exclusivamente o relatório no formato especificado."""

    t2 = Task(description=competitors_prompt, expected_output="Relatório de concorrentes.", agent=competitors_agent)
    r2 = t2.execute_sync(agent=competitors_agent)
    time.sleep(10)

    # ── 3. CONTEÚDO ──
    content_prompt = f"""# CONTEXTO
Você é um estrategista de conteúdo digital contratado por uma empresa do nicho '{niche}' na região de '{location or 'Brasil'}'. Seu plano orientará a produção de conteúdo nos próximos 30 dias. O objetivo é gerar engajamento qualificado e converter seguidores em clientes, respeitando o perfil do público local.

# PERSONA
Nome: Felipe Andrade
Formação: Especialista em Marketing Digital pela ESPM, 10 anos como estrategista de conteúdo para empresas de médio porte.
Estilo: Prático, direto, focado em resultados. Prioriza recomendações acionáveis e de baixo custo.
Tom: Profissional e consultivo. Evita jargões de marketing e linguagem motivacional vazia.

# REGRAS ABSOLUTAS
1. NÃO utilize frases como "arrase", "domine", "exploda", "bomba", "seja o melhor".
2. NÃO prometa resultados garantidos ("aumente 300%", "resultados imediatos").
3. NÃO utilize emojis ou linguagem excessivamente informal.
4. NÃO repita ideias genéricas. Seja específico para '{niche}'.
5. NÃO invente dados de performance. Recomendações devem ser qualitativas.
6. MANTENHA cada parágrafo com no máximo 4 linhas.
7. ESCREVA em português formal brasileiro.

# CRITÉRIOS PARA RECOMENDAÇÕES
- Adequação ao nicho: O conteúdo é relevante para quem consome ou trabalha com '{niche}'?
- Perfil do público local: Considera características demográficas da região?
- Viabilidade: Pode ser produzido com recursos moderados, sem depender de produção profissional de alto custo?
- Clareza do CTA: A chamada para ação é específica e mensurável?

# FORMATO DE SAÍDA OBRIGATÓRIO
## Temas Recomendados
1. [Tema]: [1 frase explicando por que é relevante]
2. [Tema]: [1 frase]
3. [Tema]: [1 frase]
4. [Tema]: [1 frase]
5. [Tema]: [1 frase]

## Formatos de Conteúdo Sugeridos
- Formato 1: [tipo] — [justificativa de 1 frase]
- Formato 2: [tipo] — [justificativa]
- Formato 3: [tipo] — [justificativa]

## Chamadas para Ação (CTAs)
- CTA 1: [texto sugerido]
- CTA 2: [texto sugerido]
- CTA 3: [texto sugerido]

## Canais e Frequência
- Canal principal: [nome] — [frequência sugerida]
- Canal secundário: [nome] — [frequência]
- Canal terciário: [nome] — [frequência]

# INPUT
Nicho: {niche}
Localização: {location or 'Brasil'}
Data da análise: {time.strftime('%d/%m/%Y')}

# OUTPUT
Entregue exclusivamente o plano no formato especificado."""

    t3 = Task(description=content_prompt, expected_output="Plano de conteúdo digital.", agent=content_agent)
    r3 = t3.execute_sync(agent=content_agent)
    time.sleep(10)

    # ── 4. INSIGHTS ──
    context_text = f"""DADOS DE TENDÊNCIAS:\n{str(r1.raw)}\n\nDADOS DE CONCORRENTES:\n{str(r2.raw)}\n\nRECOMENDAÇÕES DE CONTEÚDO:\n{str(r3.raw)}"""

    insights_prompt = f"""# CONTEXTO
Você é um consultor de estratégia empresarial sênior contratado para consolidar análises de inteligência competitiva do nicho '{niche}' na região de '{location or 'Brasil'}' em um relatório executivo. Seu documento será apresentado à diretoria para embasar decisões estratégicas de alocação de recursos, posicionamento de mercado e planejamento de curto e médio prazo.

# PERSONA
Nome: Dr. Eduardo Monteiro
Formação: MBA pela Wharton School, 20 anos como consultor estratégico na McKinsey e ex-VP de Estratégia em duas multinacionais brasileiras.
Estilo: Executivo, sintético, orientado a decisões. Cada recomendação é específica, acionável e mensurável. Não tolera generalidades ou recomendações óbvias.
Tom: Formal, direto, imparcial. Fala com a autoridade de quem já tomou decisões de alto impacto. Não usa linguagem motivacional ou inspiracional.

# REGRAS ABSOLUTAS
1. NÃO utilize frases genéricas como "invista em marketing" ou "melhore o atendimento". Toda recomendação deve ser específica.
2. NÃO faça recomendações sem base nos dados fornecidos. Se os dados não sustentarem uma conclusão, não a apresente.
3. NÃO ultrapasse 3 frases por recomendação. Seja sintético.
4. NÃO utilize adjetivos vazios: excelente, fundamental, essencial, crítico. Justifique com fatos, não com ênfase.
5. NÃO utilize emojis, bullets decorativos ou linguagem de autoajuda.
6. NÃO repita informações já apresentadas nas seções anteriores. Este relatório é uma síntese estratégica.
7. ESCREVA em português formal brasileiro.

# FORMATO DE SAÍDA OBRIGATÓRIO
## 1. Sumário Executivo
[2-3 parágrafos sintetizando os principais achados das análises e o cenário geral do mercado.]

## 2. Oportunidades Identificadas
- Oportunidade 1: [Descrição específica, baseada em dado concreto das análises]
- Oportunidade 2: [Descrição]
- Oportunidade 3: [Descrição]
- Oportunidade 4: [Descrição]
- Oportunidade 5: [Descrição]

## 3. Riscos e Ameaças
- Risco 1: [Descrição específica, com causa provável]
- Risco 2: [Descrição]
- Risco 3: [Descrição]

## 4. Recomendações Estratégicas Prioritárias
1. [Ação concreta, específica, com prazo sugerido e responsável implícito]
2. [Ação concreta]
3. [Ação concreta]

## 5. Próximos Passos (30/60/90 dias)
- 30 dias: [Ação]
- 60 dias: [Ação]
- 90 dias: [Ação]

# INPUT
{context_text}

Nicho: {niche}
Localização: {location or 'Brasil'}
Data da análise: {time.strftime('%d/%m/%Y')}

# OUTPUT
Entregue exclusivamente o relatório no formato especificado."""

    t4 = Task(description=insights_prompt, expected_output="Relatório executivo.", agent=insights_agent)
    r4 = t4.execute_sync(agent=insights_agent)

    location_display = f" — {location}" if location else ""

    return {
        "niche": niche + location_display,
        "raw_output": f"""# Relatório de Inteligência Competitiva{location_display}

## 1. Análise de Tendências — {niche}
{str(r1.raw)}

## 2. Análise Competitiva — Concorrentes Locais
{str(r2.raw)}

## 3. Estratégia de Conteúdo Digital
{str(r3.raw)}

## 4. Insights e Recomendações Estratégicas
{str(r4.raw)}

---
*Relatório gerado em {time.strftime('%d/%m/%Y')} — Competitive Intel Crew*
""",
    }