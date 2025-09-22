CREATE TABLE users (
    username TEXT PRIMARY KEY,
    disabled BOOLEAN DEFAULT FALSE,
    admin BOOLEAN DEFAULT FALSE,
    hashed_password TEXT NOT NULL
);

CREATE TABLE templates (
    name TEXT PRIMARY KEY,
    image TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT 'latest',
    default_env TEXT,
    additional_env TEXT,
    resource_min_cpu INTEGER,
    resource_min_disk INTEGER,
    resource_min_mem INTEGER
);

CREATE TABLE nodes (
    "cpus" integer,
    "disk" integer,
    "memory" integer,
    "cpu_name" text NOT NULL,
    "max_hz" smallint NOT NULL,
    "id" text,
    "arch" arch NOT NULL
)