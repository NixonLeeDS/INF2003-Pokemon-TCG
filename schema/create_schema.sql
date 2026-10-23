CREATE DATABASE IF NOT EXISTS inf2003_pokemon
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE inf2003_pokemon;

DROP VIEW IF EXISTS user_collection_summary;
DROP TABLE IF EXISTS trade_item;
DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS wishlist_item;
DROP TABLE IF EXISTS collection_item;
DROP TABLE IF EXISTS card_type;
DROP TABLE IF EXISTS cards;
DROP TABLE IF EXISTS sets;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE sets (
    set_id VARCHAR(32) PRIMARY KEY,
    set_name VARCHAR(120) NOT NULL,
    series VARCHAR(120),
    publisher VARCHAR(80),
    generation VARCHAR(80),
    release_date DATE,
    UNIQUE KEY uq_set_identity (set_id, set_name)
) ENGINE=InnoDB;

CREATE TABLE cards (
    card_id VARCHAR(48) PRIMARY KEY,
    set_id VARCHAR(32) NOT NULL,
    card_name VARCHAR(160) NOT NULL,
    card_number VARCHAR(30),
    supertype VARCHAR(60),
    subtype_summary VARCHAR(255),
    level INT NULL,
    hp INT NULL,
    rarity VARCHAR(100),
    artist VARCHAR(160),
    evolves_from VARCHAR(160),
    converted_retreat_cost INT NULL,
    flavor_text TEXT NULL,
    regulation_mark VARCHAR(20) NULL,
    CONSTRAINT fk_cards_set FOREIGN KEY (set_id) REFERENCES sets(set_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_cards_hp CHECK (hp IS NULL OR hp >= 0),
    CONSTRAINT chk_cards_retreat CHECK (converted_retreat_cost IS NULL OR converted_retreat_cost >= 0)
) ENGINE=InnoDB;

CREATE TABLE card_type (
    card_id VARCHAR(48) NOT NULL,
    type VARCHAR(50) NOT NULL,
    PRIMARY KEY (card_id, type),
    CONSTRAINT fk_card_type_card FOREIGN KEY (card_id) REFERENCES cards(card_id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE collection_item (
    user_id INT NOT NULL,
    card_id VARCHAR(48) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    trade_quantity INT NOT NULL DEFAULT 0,
    added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, card_id),
    CONSTRAINT fk_collection_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_collection_card FOREIGN KEY (card_id) REFERENCES cards(card_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_collection_quantity CHECK (quantity >= 0),
    CONSTRAINT chk_collection_trade_quantity CHECK (trade_quantity >= 0 AND trade_quantity <= quantity)
) ENGINE=InnoDB;

CREATE TABLE wishlist_item (
    user_id INT NOT NULL,
    card_id VARCHAR(48) NOT NULL,
    priority TINYINT NOT NULL DEFAULT 3,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, card_id),
    CONSTRAINT fk_wishlist_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_wishlist_card FOREIGN KEY (card_id) REFERENCES cards(card_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_wishlist_priority CHECK (priority BETWEEN 1 AND 5)
) ENGINE=InnoDB;

CREATE TABLE trades (
    trade_id INT AUTO_INCREMENT PRIMARY KEY,
    requester_id INT NOT NULL,
    recipient_id INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_trade_requester FOREIGN KEY (requester_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_trade_recipient FOREIGN KEY (recipient_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_trade_distinct_users CHECK (requester_id <> recipient_id),
    CONSTRAINT chk_trade_status CHECK (status IN ('PENDING','ACCEPTED','REJECTED','CANCELLED','COMPLETED'))
) ENGINE=InnoDB;

CREATE TABLE trade_item (
    trade_item_id INT AUTO_INCREMENT PRIMARY KEY,
    trade_id INT NOT NULL,
    card_id VARCHAR(48) NOT NULL,
    owner_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    CONSTRAINT fk_trade_item_trade FOREIGN KEY (trade_id) REFERENCES trades(trade_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_trade_item_card FOREIGN KEY (card_id) REFERENCES cards(card_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_trade_item_owner FOREIGN KEY (owner_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_trade_item_quantity CHECK (quantity > 0),
    UNIQUE KEY uq_trade_owner_card (trade_id, owner_id, card_id)
) ENGINE=InnoDB;

CREATE INDEX idx_cards_name ON cards(card_name);
CREATE INDEX idx_cards_set ON cards(set_id);
CREATE INDEX idx_cards_rarity ON cards(rarity);
CREATE INDEX idx_collection_card_trade ON collection_item(card_id, trade_quantity);
CREATE INDEX idx_wishlist_card ON wishlist_item(card_id);
CREATE INDEX idx_trades_status ON trades(status);

CREATE OR REPLACE VIEW user_collection_summary AS
SELECT
    u.user_id,
    u.username,
    COUNT(DISTINCT ci.card_id) AS unique_cards,
    COALESCE(SUM(ci.quantity), 0) AS total_cards,
    COALESCE(SUM(ci.trade_quantity), 0) AS tradeable_cards,
    COUNT(DISTINCT c.set_id) AS sets_collected
FROM users u
LEFT JOIN collection_item ci ON ci.user_id = u.user_id
LEFT JOIN cards c ON c.card_id = ci.card_id
GROUP BY u.user_id, u.username;
