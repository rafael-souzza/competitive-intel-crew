import streamlit as st
from orchestrator import run_analysis
import time

st.set_page_config(
    page_title="Competitive Intel Crew",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Competitive Intel Crew")
st.caption("Sistema multi-agente de inteligência competitiva")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuração")
    niche = st.text_input("Nicho ou Empresa", placeholder="Ex: academia premium")
    location = st.text_input("Localização", placeholder="Ex: Pinheiros, São Paulo")
    
    st.divider()
    st.subheader("🏪 Dados da Sua Loja")
    st.caption("Preencha para receber comparativo e score")
    my_name = st.text_input("Nome do negócio", placeholder="Ex: Celulares Brás Center")
    my_price = st.text_input("Preço médio", placeholder="Ex: R$ 1.200")
    my_services = st.text_area("Serviços oferecidos", placeholder="Ex: Venda, troca, assistência técnica, acessórios")
    my_digital = st.selectbox("Presença digital", ["Nenhuma", "Apenas WhatsApp", "Instagram/Facebook", "Site próprio", "Site + Redes + Ads"])
    
    run = st.button("🚀 Iniciar Análise", type="primary", use_container_width=True)
    
    st.divider()
    st.markdown("**Agentes ativos:**")
    st.markdown("🔍 Analista de Tendências")
    st.markdown("📊 Analista Competitivo")
    st.markdown("✍️ Estrategista de Conteúdo")
    st.markdown("🧠 Consultor de Insights")

# Área principal
if not niche:
    st.info("👈 Insira um nicho e localização na barra lateral e clique em **Iniciar Análise**.")
else:
    if run:
        with st.spinner("🔄 Agentes trabalhando... Isso pode levar 1-2 minutos."):
            progress = st.progress(0, text="Iniciando orquestrador...")
            time.sleep(0.5)
            progress.progress(25, text="🔍 Analista de Tendências pesquisando...")
            time.sleep(0.5)
            progress.progress(50, text="📊 Analista Competitivo mapeando...")
            time.sleep(0.5)
            progress.progress(75, text="✍️ Estrategista de Conteúdo criando...")
            time.sleep(0.5)
            progress.progress(90, text="🧠 Consultor cruzando dados...")
            
            result = run_analysis(niche, location)
            
            progress.progress(100, text="✅ Análise concluída!")
            time.sleep(0.5)
            progress.empty()

        loc_text = f" — {location}" if location else ""
        st.success(f"✅ Análise concluída para: **{niche}{loc_text}**")
        
        # Diagnóstico do Negócio
        if my_name:
            st.markdown("---")
            st.subheader(f"📊 Diagnóstico: {my_name}")
            
            digital_score = {"Nenhuma": 10, "Apenas WhatsApp": 30, "Instagram/Facebook": 55, "Site próprio": 75, "Site + Redes + Ads": 95}
            score = 50 + (digital_score.get(my_digital, 30) - 50) * 0.4
            if my_price:
                score += 10
            if len(my_services) > 30:
                score += 10
            
            score = min(98, max(30, int(score)))
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Score de Competitividade", f"{score}/100", delta=f"{score - 55} pts vs. média" if score > 55 else f"{score - 55} pts vs. média")
            with col2:
                st.metric("Presença Digital", my_digital, delta="+" if digital_score.get(my_digital, 0) > 50 else "-")
            with col3:
                st.metric("Preço Informado", my_price or "N/I", delta="Preenchido" if my_price else "Não informado")
            with col4:
                serv_count = len([s for s in my_services.split(",") if s.strip()]) if my_services else 0
                st.metric("Serviços", f"{serv_count} listados", delta="Completo" if serv_count >= 3 else "Básico")
            
            st.markdown("---")
            st.subheader("🚨 Alertas e Recomendações")
            
            alerts = []
            if score < 50:
                alerts.append(f"⚠️ **Score baixo ({score}/100):** Seu negócio está abaixo da média competitiva da região. Priorize melhorar a presença digital e diversificar serviços.")
            elif score < 75:
                alerts.append(f"📈 **Score moderado ({score}/100):** Há espaço para crescimento. Considere expandir seus canais digitais.")
            else:
                alerts.append(f"✅ **Score competitivo ({score}/100):** Seu negócio está bem posicionado. Mantenha o monitoramento para sustentar a vantagem.")
            
            if digital_score.get(my_digital, 0) < 50:
                alerts.append(f"📱 **Presença digital limitada:** Seu nível atual é '{my_digital}'. A maioria dos concorrentes já utiliza redes sociais ou site próprio.")
            
            if my_price:
                alerts.append(f"💰 **Preço informado ({my_price}):** Compare com a faixa de preços dos concorrentes na seção de análise competitiva para verificar se seu posicionamento está adequado.")
            
            if serv_count < 3:
                alerts.append(f"🔧 **Poucos serviços listados ({serv_count}):** Diversificar serviços pode aumentar sua vantagem competitiva.")
            
            for alert in alerts:
                st.warning(alert)
        
        st.markdown("---")
        
        with st.expander("📄 Relatório Completo", expanded=True):
            st.markdown(result["raw_output"])
        
        st.download_button(
            "📥 Exportar Relatório (Markdown)",
            data=result["raw_output"],
            file_name=f"analise_{niche.replace(' ', '_')}.md",
            mime="text/markdown",
        )