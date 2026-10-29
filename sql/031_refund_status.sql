ALTER TABLE approval_requests
    ADD COLUMN IF NOT EXISTS refund_status TEXT;

ALTER TABLE approval_requests
    DROP CONSTRAINT IF EXISTS approval_requests_refund_status_check;

ALTER TABLE approval_requests
    ADD CONSTRAINT approval_requests_refund_status_check
    CHECK (refund_status IN ('pending', 'succeeded', 'failed'));

UPDATE approval_requests a
SET refund_status = r.status
FROM refund_transactions r
WHERE r.approval_id = a.id AND a.refund_status IS NULL;

UPDATE approval_requests
SET refund_status = 'failed'
WHERE action_type IN ('refund', 'customer_service_refund')
  AND status = 'approved' AND refund_status IS NULL;
