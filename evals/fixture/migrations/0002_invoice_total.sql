-- 0002: add a total to invoices.
ALTER TABLE invoices
  ADD COLUMN total INTEGER NOT NULL DEFAULT 0;
-- end
