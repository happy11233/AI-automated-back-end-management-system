ALTER TABLE users
ADD COLUMN IF NOT EXISTS position TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'users_position_check'
    ) THEN
        ALTER TABLE users
        ADD CONSTRAINT users_position_check
        CHECK (position IS NULL OR position IN ('operations', 'customer_service', 'finance'));
    END IF;
END $$;

UPDATE users
SET position = 'customer_service'
WHERE role = 'employee'
  AND position IS NULL;

UPDATE users
SET department = '客服部'
WHERE role = 'employee'
  AND position = 'customer_service'
  AND (department IS NULL OR department = '');

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_position ON users(position);
