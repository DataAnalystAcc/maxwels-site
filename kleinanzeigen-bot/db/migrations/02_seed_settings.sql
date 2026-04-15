-- Kleinanzeigen Bot — Default Settings
-- Seeded on first boot.

INSERT INTO settings (key, value) VALUES
    ('default_zip', '10115'),
    ('default_price_strategy', 'competitive'),
    ('posting_delay_min_sec', '30'),
    ('posting_delay_max_sec', '60'),
    ('posting_max_per_session', '10'),
    ('allowed_telegram_chat_id', '0')
ON CONFLICT (key) DO NOTHING;
