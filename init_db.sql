-- PostgreSQL database schema for meetings table
-- Run this script to initialize the database
-- Note: CREATE DATABASE must be run as a separate command:
-- psql -U postgres -c "CREATE DATABASE meetings_db;"
-- Then run: psql -U postgres -d meetings_db -f init_db.sql

CREATE TABLE IF NOT EXISTS meetings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    meeting_date DATE NOT NULL,
    meeting_time TIME,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on meeting_date for faster queries
CREATE INDEX IF NOT EXISTS idx_meeting_date ON meetings(meeting_date);

-- Create index on meeting_date and meeting_time for conflict checking
CREATE INDEX IF NOT EXISTS idx_meeting_datetime ON meetings(meeting_date, meeting_time);
