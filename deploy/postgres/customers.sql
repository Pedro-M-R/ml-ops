-- Executado pelo entrypoint em um volume novo. Uma falha desfaz toda a importação.
BEGIN;
CREATE TEMP TABLE customer_import (
    "customerID" text, gender text, "SeniorCitizen" text, "Partner" text,
    "Dependents" text, tenure text, "PhoneService" text, "MultipleLines" text,
    "InternetService" text, "OnlineSecurity" text, "OnlineBackup" text,
    "DeviceProtection" text, "TechSupport" text, "StreamingTV" text,
    "StreamingMovies" text, "Contract" text, "PaperlessBilling" text,
    "PaymentMethod" text, "MonthlyCharges" text, "TotalCharges" text, "Churn" text
);
\copy customer_import FROM '/seed/churn.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

CREATE TABLE public.customers AS SELECT
    btrim("customerID") AS "customerID", gender,
    NULLIF(btrim("SeniorCitizen"), '')::integer AS "SeniorCitizen",
    "Partner", "Dependents", NULLIF(btrim(tenure), '')::double precision AS tenure,
    "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
    NULLIF(btrim("MonthlyCharges"), '')::double precision AS "MonthlyCharges",
    NULLIF(btrim("TotalCharges"), '')::double precision AS "TotalCharges"
FROM customer_import;
ALTER TABLE public.customers ADD PRIMARY KEY ("customerID");
ALTER TABLE public.customers ADD CHECK ("customerID" <> '');
ALTER TABLE public.customers ADD CHECK ("SeniorCitizen" IN (0, 1));
ALTER TABLE public.customers ADD CHECK (tenure >= 0 AND "MonthlyCharges" >= 0 AND "TotalCharges" >= 0);
CREATE UNIQUE INDEX customers_normalized_id ON public.customers (lower("customerID"));

CREATE ROLE churn_reader LOGIN PASSWORD :'reader_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON public.customers FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO churn_reader;
GRANT SELECT ON public.customers TO churn_reader;
ALTER ROLE churn_reader SET default_transaction_read_only = on;
COMMIT;
