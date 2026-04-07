-- Supabase SQL schema for malaga-flight-tracker
-- Run this in the Supabase SQL Editor to set up all tables

-- Apartment calendars
CREATE TABLE apartments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    google_calendar_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Route settings (editable from dashboard)
CREATE TABLE settings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    route_from TEXT NOT NULL,
    route_to TEXT NOT NULL DEFAULT 'AGP',
    currency TEXT NOT NULL DEFAULT 'EUR',
    price_threshold NUMERIC,
    look_ahead_days INTEGER NOT NULL DEFAULT 60,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Current prices (upserted each run)
CREATE TABLE prices (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    route_from TEXT NOT NULL,
    route_to TEXT NOT NULL,
    departure_date DATE NOT NULL,
    price NUMERIC,
    currency TEXT NOT NULL DEFAULT 'EUR',
    airline TEXT,
    booking_link TEXT,
    checked_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (route_from, route_to, departure_date)
);

-- Price history for trend charts
CREATE TABLE price_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    route_from TEXT NOT NULL,
    route_to TEXT NOT NULL,
    departure_date DATE NOT NULL,
    price NUMERIC,
    currency TEXT NOT NULL DEFAULT 'EUR',
    checked_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX idx_prices_route ON prices (route_from, route_to);
CREATE INDEX idx_prices_date ON prices (departure_date);
CREATE INDEX idx_history_route_date ON price_history (route_from, route_to, departure_date);
CREATE INDEX idx_history_checked ON price_history (checked_at);

-- Enable Row Level Security (required by Supabase)
ALTER TABLE apartments ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;

-- Allow public read access (dashboard uses anon key)
CREATE POLICY "Allow public read" ON apartments FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON settings FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON prices FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON price_history FOR SELECT USING (true);

-- Allow public write for settings (dashboard edits thresholds)
CREATE POLICY "Allow public update" ON settings FOR UPDATE USING (true);

-- Allow insert/update for prices (GitHub Actions writes via anon key)
CREATE POLICY "Allow public insert" ON prices FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update" ON prices FOR UPDATE USING (true);
CREATE POLICY "Allow public insert" ON price_history FOR INSERT WITH CHECK (true);

-- Seed default routes
INSERT INTO settings (route_from, route_to, currency, price_threshold, look_ahead_days) VALUES
    ('CPH', 'AGP', 'DKK', 500, 60),
    ('GOT', 'AGP', 'SEK', 600, 60),
    ('ARN', 'AGP', 'SEK', 600, 60);

-- Seed example apartments (update google_calendar_id after setup)
INSERT INTO apartments (name, google_calendar_id) VALUES
    ('Apartment 1', 'your-calendar-id-1@group.calendar.google.com'),
    ('Apartment 2', 'your-calendar-id-2@group.calendar.google.com');
