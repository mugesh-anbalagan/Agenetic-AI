#!/bin/bash
# Database setup script for PostgreSQL

# Set variables (adjust as needed)
DB_USER=${DB_USER:-postgres_prdp}
DB_NAME=${DB_NAME:-meetings_db_prdp}

# Create database (requires superuser privileges)
psql -U $DB_USER -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "Database $DB_NAME may already exist"

# Run schema creation
psql -U $DB_USER -d $DB_NAME -f init_db.sql || {
    echo "Running schema creation manually..."
    psql -U $DB_USER -d $DB_NAME <<EOF
CREATE TABLE IF NOT EXISTS meetings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    meeting_date DATE NOT NULL,
    meeting_time TIME,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_meeting_date ON meetings(meeting_date);
CREATE INDEX IF NOT EXISTS idx_meeting_datetime ON meetings(meeting_date, meeting_time);
EOF
}

echo "Database setup complete!"

