# Sentinel-01

## AETHEL Foundation - Agente de Proteção de Capital ERC-8004

<p align="center">
  <img src="https://img.shields.io/badge/ERC--8004-Compatível-cyan" alt="ERC-8004 Compatível">
  <img src="https://img.shields.io/badge/Status-Demo%20Ready-green" alt="Status">
  <img src="https://img.shields.io/badge/Licença-MIT-blue" alt="Licença">
</p>

> **Preservação de capital é mandatória. Lucro é secundário.**

Sentinel-01 é um agente de trading AI soberano e risk-first construído para o padrão ERC-8004. Diferente de bots de trading tradicionais que buscam lucro, o Sentinel-01 opera sob um framework de governança constitucional onde conformidade com políticas e preservação de capital prevalecem sobre comportamento oportunista.

## Características Principais

- **Arquitetura Risk-First**: Toda decisão passa por um checklist pré-trade determinístico
- **Governança Constitucional**: Governança on-chain controla todos os parâmetros
- **Decisões Auditáveis**: ValidationArtifacts registram cada ciclo para verificação
- **Consciente de Regime**: Adapta comportamento automaticamente baseado nas condições de mercado
- **Pronto para ERC-8004**: Preparado para identidade e verificação on-chain

## Início Rápido

### Pré-requisitos

- Python 3.11+
- Node.js 18+
- MongoDB

### Setup do Backend

```bash
cd backend
pip install -r requirements.txt
```

### Setup do Frontend

```bash
cd frontend
yarn install
```

### Executar em Modo Simulação

```bash
# Iniciar backend
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Iniciar frontend (terminal separado)
cd frontend
yarn start
```

### Acessar Dashboard

Abra `http://localhost:3000` para o dashboard web.

## Arquitetura

```
sentinel-01/
├── backend/
│   ├── agent/           # Módulos core do agente
│   │   ├── config.py         # Parâmetros de risco & constantes
│   │   ├── signal_engine.py  # Processamento de sinais
│   │   ├── risk_engine.py    # Checklist de risco pré-trade
│   │   ├── policy_engine.py  # Classificação de regime & política
│   │   ├── executor.py       # Construção & execução de TradeIntent
│   │   ├── reputation_tracker.py  # ValidationArtifacts
│   │   └── main.py           # Loop de orquestração
│   ├── governance/      # Controle constitucional
│   │   ├── governance.py     # Propostas, votação, execução
│   │   └── emergency_protocol.py  # Resposta a crises
│   ├── adapters/        # Integrações externas
│   │   └── market_data.py    # Adaptador CoinGecko
│   ├── specs/           # Especificações (fonte de verdade)
│   └── server.py        # API FastAPI
└── frontend/            # Dashboard React
```

## Limites de Risco (Constitucionais)

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| Max Drawdown | 5% | Drawdown máximo do portfólio |
| Max Trade Único | 2% | Tamanho máximo de trade único |
| Max Perda Diária | 3% | Perda diária máxima |
| Max Posição | 20% | Posição única máxima |
| Min Liquidez | 30% | Ratio mínimo de cash |
| Max Alavancagem | 1x | Sem alavancagem |

## Regimes de Mercado

| Regime | Comportamento |
|--------|---------------|
| **NORMAL** | Todas ações permitidas, sizing padrão |
| **VOLATILE** | Defensivo, sizing reduzido |
| **CRISIS** | Apenas HOLD, preservação de capital |
| **UNKNOWN** | Conservador, aguardar clareza |

## Endpoints da API

### Agente
- `GET /api/agent/status` - Status do agente
- `POST /api/agent/cycle` - Executar ciclo único
- `POST /api/agent/start` - Iniciar operação contínua
- `POST /api/agent/stop` - Parar agente

### Mercado
- `GET /api/market/price/{asset}` - Preço em tempo real
- `GET /api/market/signal/{asset}` - Sinal processado

### Governança
- `GET /api/governance/proposals` - Listar propostas
- `POST /api/governance/proposals` - Criar proposta
- `POST /api/governance/proposals/{id}/vote` - Votar

### Emergência
- `POST /api/emergency/pause` - Pausar trading
- `POST /api/emergency/resume` - Retomar trading

## Pontos de Integração ERC-8004

### Pronto Agora (Simulação)
- Estrutura e assinatura de TradeIntent
- Geração de ValidationArtifact
- Computação de policy hash
- Rastreamento de métricas de reputação

### TODO para Produção
- [ ] Conectar ao ERC-8004 Identity Registry
- [ ] Implementar assinatura EIP-712 com chaves reais
- [ ] Publicar ValidationArtifacts on-chain
- [ ] Conectar ao contrato Risk Router
- [ ] Integração real de wallet

## Demo

Execute a simulação para ver o Sentinel-01 em ação:

```bash
# Executar 10 ciclos de decisão
POST /api/agent/start?cycles=10

# Ou executar ciclo único
POST /api/agent/cycle?asset=ETH
```

Observe no dashboard:
- Transições de regime
- Avaliações de risco
- Geração de ValidationArtifact
- Mudanças no estado do portfólio

## Filosofia

> "Uma oportunidade perdida é recuperável. Uma violação de política não é."

Sentinel-01 incorpora o princípio de que gestão de risco institucional requer conformidade absoluta com políticas. O agente sempre escolherá preservação de capital sobre lucro potencial.

---

**AETHEL Foundation** | Construindo o futuro de agentes financeiros autônomos e confiáveis.
