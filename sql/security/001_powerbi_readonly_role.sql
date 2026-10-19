-- LOGIFLOW AI | POWER BI READ-ONLY ACCESS

-- Executar conectado ao banco logiflow.

CREATE ROLE logiflow_bi_reader
WITH LOGIN
PASSWORD 'SUBSTITUA_POR_UMA_SENHA_FORTE';

-- Permite conectar ao banco.
GRANT CONNECT ON DATABASE logiflow
TO logiflow_bi_reader;

-- Permite acessar o schema analytics.
GRANT USAGE ON SCHEMA analytics
TO logiflow_bi_reader;

-- Permite consultar as cinco views existentes.
GRANT SELECT ON ALL TABLES IN SCHEMA analytics
TO logiflow_bi_reader;

-- Permite consultar futuras views criadas pelo usuário logiflow.
ALTER DEFAULT PRIVILEGES FOR ROLE logiflow
IN SCHEMA analytics
GRANT SELECT ON TABLES TO logiflow_bi_reader;