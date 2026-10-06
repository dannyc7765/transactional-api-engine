CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    wallet_balance NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (wallet_balance >= 0)
);

CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price NUMERIC(12, 2) NOT NULL,
    stock INT NOT NULL CHECK (stock >= 0)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    item_id VARCHAR(100) NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    total_amount NUMERIC(12, 2) NOT NULL,
    status VARCHAR(50) NOT NULL
);

-- Seed baseline product referenced in race conditions test
INSERT INTO products (product_id, name, price, stock)
VALUES ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Limited Item', 10.00, 1)
ON CONFLICT (product_id) DO NOTHING;
