-- Schema de la base de données d'état du framework

-- Table des déploiements
CREATE TABLE IF NOT EXISTS deployments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    profile TEXT,
    status TEXT NOT NULL DEFAULT 'PLANNED',  -- PLANNED, IN_PROGRESS, PAUSED, COMPLETED, FAILED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Table des outils dans un déploiement
CREATE TABLE IF NOT EXISTS deployment_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deployment_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    version TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED
    install_order INTEGER,
    config_json TEXT,
    FOREIGN KEY (deployment_id) REFERENCES deployments(id) ON DELETE CASCADE
);

-- Table des checkpoints (reprise après interruption)
CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    deployment_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    step TEXT NOT NULL,  -- PREREQ_CHECK, BACKUP, INSTALL, CONFIGURE, VALIDATE
    state_data TEXT,     -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deployment_id) REFERENCES deployments(id) ON DELETE CASCADE
);

-- Table des sauvegardes
CREATE TABLE IF NOT EXISTS backups (
    id TEXT PRIMARY KEY,
    deployment_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    backup_path TEXT NOT NULL,
    backup_type TEXT NOT NULL,  -- PRE_INSTALL, CONFIG, FULL
    size_bytes INTEGER,
    checksum TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deployment_id) REFERENCES deployments(id) ON DELETE CASCADE
);

-- Table des journaux d'exécution (optionnelle, pour historique rapide)
CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deployment_id TEXT NOT NULL,
    tool_name TEXT,
    log_level TEXT NOT NULL,  -- DEBUG, INFO, WARNING, ERROR
    message TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deployment_id) REFERENCES deployments(id) ON DELETE CASCADE
);

-- Index pour accélérer les recherches
CREATE INDEX IF NOT EXISTS idx_deployment_tools_deployment ON deployment_tools(deployment_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_deployment ON checkpoints(deployment_id);
CREATE INDEX IF NOT EXISTS idx_backups_deployment ON backups(deployment_id);