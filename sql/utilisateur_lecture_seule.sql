-- Utilisateur MySQL en LECTURE SEULE pour n8n.
-- Meme si le LLM genere un DELETE, DROP ou UPDATE, MySQL le refusera.
--
-- 1. Executer ce script dans phpMyAdmin (onglet SQL) ou en ligne de commande :
--      mysql -u root -p < sql/utilisateur_lecture_seule.sql
-- 2. Dans n8n, modifier le credential "MySQL account" :
--      User = assistant_lecture, Password = le mot de passe choisi ci-dessous
--
-- Remplacez 'ChangezCeMotDePasse' avant d'executer le script.

CREATE USER IF NOT EXISTS 'assistant_lecture'@'localhost' IDENTIFIED BY 'ChangezCeMotDePasse';

-- Acces uniquement en lecture, et uniquement aux 5 vues utilisees par l'assistant
GRANT SELECT ON cms.view_customer_invoice    TO 'assistant_lecture'@'localhost';
GRANT SELECT ON cms.view_product             TO 'assistant_lecture'@'localhost';
GRANT SELECT ON cms.vw_achat_entetes         TO 'assistant_lecture'@'localhost';
GRANT SELECT ON cms.vw_achat                 TO 'assistant_lecture'@'localhost';
GRANT SELECT ON cms.vw_achat_kpi_fournisseur TO 'assistant_lecture'@'localhost';

FLUSH PRIVILEGES;
