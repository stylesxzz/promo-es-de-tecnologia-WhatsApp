# Promo Tech WhatsApp

Bot em nuvem para descobrir produtos de tecnologia no Mercado Livre, organizar ofertas e preparar até **15 publicações por dia** para um canal público do WhatsApp.

> **Estado inicial seguro:** descoberta automática e fila de ofertas funcionam. A publicação automática em Canais do WhatsApp fica desativada: a API pública oficial do WhatsApp Business não oferece um endpoint geral documentado para publicar atualizações em Canais. O painel gera o texto pronto para revisão e publicação manual. Não use automação não oficial de WhatsApp Web.

## Funcionalidades
- Busca de produtos via API pública de busca do Mercado Livre (site MLB).
- Filtros básicos por categorias/termos de tecnologia, preço e qualidade dos dados.
- Fila SQLite com deduplicação por item.
- Limite diário configurável (padrão: 15), intervalo e horários.
- Painel web para revisar, aprovar, copiar e marcar ofertas como publicadas.
- Link de afiliado por produto: cole o link gerado no Portal de Afiliados. O sistema não fabrica nem altera links rastreados.
- Docker e deploy em serviço de nuvem com volume persistente.

## Arquitetura
```text
Mercado Livre public search API
          |
          v
  Discovery worker (scheduler)
          |
          v
   Validation + deduplication
          |
          v
 SQLite offers queue <----> FastAPI dashboard/API
          |
          v
 Human review + affiliate URL
          |
          v
 WhatsApp Channel (manual publish)
```

## Requisitos
- Docker + Docker Compose (recomendado) ou Python 3.11+.
- Conta aprovada no Programa de Afiliados e Criadores do Mercado Livre.
- Canal público do WhatsApp, se esse canal estiver permitido nas regras atuais do seu programa.

## Instalação rápida
1. Clone:
   ```bash
   git clone https://github.com/stylesxzz/promo-es-de-tecnologia-WhatsApp.git
   cd promo-es-de-tecnologia-WhatsApp
   ```
2. Crie a configuração:
   ```bash
   cp .env.example .env
   ```
3. Ajuste `.env` (principalmente `ADMIN_TOKEN`).
4. Suba:
   ```bash
   docker compose up -d --build
   ```
5. Abra `http://localhost:8000`. Informe o token administrativo no campo de acesso.

## Executar sem Docker
```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Configuração
Veja `.env.example`. A busca usa a API pública de itens do Mercado Livre; disponibilidade, campos e limites podem mudar. O worker não presume que um produto esteja em promoção: preço e desconto só são exibidos quando os dados permitem comparação confiável.

### Links de afiliado
1. Entre no Portal de Afiliados e Criadores do Mercado Livre.
2. Gere o link de afiliado do produto escolhido.
3. No painel, abra a oferta e cole o link gerado no campo **Link de afiliado**.
4. Não substitua por link comum nem tente construir parâmetros de rastreamento manualmente.

O sistema não solicita senha da conta Mercado Livre e não faz scraping autenticado.

## WhatsApp: limite importante
WhatsApp Channels são publicações unidirecionais. A WhatsApp Business Platform/Cloud API documenta mensagens para conversas comerciais, mas não fornece um método geral público para publicar atualizações em Canais. Por isso, este projeto prepara e agenda o conteúdo, mas exige copiar/publicar no próprio canal. Não conecte bibliotecas que automatizam WhatsApp Web com sua conta principal.

Antes de divulgar, confira os Termos do Programa de Afiliados: o Mercado Livre restringe a divulgação em grupos privados e exige canais de divulgação permitidos/declarados. Use somente canais públicos aceitos e informe claramente que pode haver comissão por compras.

## Endpoints
- `GET /` painel
- `GET /api/health` saúde
- `GET /api/offers` ofertas (token admin)
- `POST /api/scan` iniciar busca (token admin)
- `POST /api/offers/{id}/affiliate-link` salvar link de afiliado (token admin)
- `POST /api/offers/{id}/status` atualizar status (token admin)
- `GET /api/stats` métricas (token admin)

Envie `X-Admin-Token: <ADMIN_TOKEN>` nas chamadas protegidas.

## Segurança e operação
- Troque `ADMIN_TOKEN` por um segredo forte.
- Use HTTPS no deploy público.
- Configure volume persistente em `/data`.
- Não faça commit de `.env`, tokens ou credenciais.
- Comece revisando as ofertas manualmente; preços e estoque mudam.
- O agendamento é local ao container; mantenha uma única réplica do worker para evitar buscas duplicadas.

## Próximas etapas para ativar
1. Definir o link de afiliado de cada produto no painel.
2. Criar/confirmar um canal público e verificar se ele está declarado/permitido no programa.
3. Publicar manualmente as ofertas aprovadas.
4. Conferir cliques e ganhos no Portal de Afiliados.

## Licença
MIT — veja [LICENSE](LICENSE).
