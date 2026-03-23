-- ============================================================================
-- TBAPS NEF Certificate Management - Database Schema
-- 
-- Tables for managing .nef VPN certificates, employee access, and audit logs
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- EMPLOYEES TABLE (if not exists)
-- ============================================================================

CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    department VARCHAR(255),
    role VARCHAR(255),
    manager_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_employee_status CHECK (status IN ('active', 'inactive', 'suspended', 'terminated'))
);

CREATE INDEX IF NOT EXISTS idx_employees_email ON employees(email);
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);

-- ============================================================================
-- VPN CERTIFICATES TABLE (Enhanced for NEF)
-- ============================================================================

-- Drop existing table if structure needs update
DROP TABLE IF EXISTS vpn_certificates CASCADE;

CREATE TABLE vpn_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Employee information
    employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
    employee_name VARCHAR(255) NOT NULL,
    employee_email VARCHAR(255) NOT NULL,
    certificate_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Certificate lifecycle
    issued_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    
    -- File information
    config_file VARCHAR(255) NOT NULL,
    checksum VARCHAR(255),
    file_size BIGINT,
    
    -- Usage tracking
    download_count INTEGER DEFAULT 0,
    last_downloaded_at TIMESTAMP,
    last_connection_at TIMESTAMP,
    total_connections INTEGER DEFAULT 0,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    
    -- Constraints
    CONSTRAINT valid_cert_status CHECK (status IN ('active', 'revoked', 'expired', 'suspended')),
    CONSTRAINT valid_dates CHECK (expires_at > issued_at)
);

-- Indexes
CREATE INDEX idx_vpn_certs_employee_id ON vpn_certificates(employee_id);
CREATE INDEX idx_vpn_certs_status ON vpn_certificates(status);
CREATE INDEX idx_vpn_certs_certificate_id ON vpn_certificates(certificate_id);
CREATE INDEX idx_vpn_certs_expires_at ON vpn_certificates(expires_at);
CREATE INDEX idx_vpn_certs_employee_email ON vpn_certificates(employee_email);

-- Comments
COMMENT ON TABLE vpn_certificates IS 'NEF VPN certificates for employee remote access';
COMMENT ON COLUMN vpn_certificates.config_file IS 'Filename of .nef configuration file';
COMMENT ON COLUMN vpn_certificates.checksum IS 'SHA256 checksum of .nef file';

-- ============================================================================
-- VPN CONNECTION LOGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS vpn_connection_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Certificate and employee
    certificate_id VARCHAR(255) NOT NULL,
    employee_id UUID REFERENCES employees(id) ON DELETE SET NULL,
    employee_name VARCHAR(255),
    
    -- Connection details
    connected_at TIMESTAMP,
    disconnected_at TIMESTAMP,
    session_duration INTERVAL,
    
    -- Network information
    ip_address INET,
    vpn_ip_address INET,
    client_version VARCHAR(100),
    
    -- Traffic statistics
    bytes_sent BIGINT DEFAULT 0,
    bytes_received BIGINT DEFAULT 0,
    packets_sent BIGINT DEFAULT 0,
    packets_received BIGINT DEFAULT 0,
    
    -- Status and errors
    status VARCHAR(50),
    error_message TEXT,
    disconnect_reason VARCHAR(255),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_connection_status CHECK (status IN ('connected', 'disconnected', 'failed', 'timeout'))
);

-- Indexes
CREATE INDEX idx_vpn_logs_certificate_id ON vpn_connection_logs(certificate_id);
CREATE INDEX idx_vpn_logs_employee_id ON vpn_connection_logs(employee_id);
CREATE INDEX idx_vpn_logs_connected_at ON vpn_connection_logs(connected_at);
CREATE INDEX idx_vpn_logs_status ON vpn_connection_logs(status);
CREATE INDEX idx_vpn_logs_ip_address ON vpn_connection_logs(ip_address);

-- Comments
COMMENT ON TABLE vpn_connection_logs IS 'VPN connection history and session logs';
COMMENT ON COLUMN vpn_connection_logs.session_duration IS 'Calculated duration of VPN session';

-- ============================================================================
-- NEF DELIVERY AUDIT TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS nef_delivery_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Certificate information
    certificate_id VARCHAR(255) NOT NULL,
    employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
    employee_email VARCHAR(255) NOT NULL,
    
    -- Delivery details
    delivery_method VARCHAR(50),
    -- Methods: 'email', 'secure_portal', 'in_person', 'api_download', 'manual'
    delivery_date TIMESTAMP DEFAULT NOW(),
    delivered_by VARCHAR(255),
    
    -- Confirmation
    recipient_confirmed BOOLEAN DEFAULT FALSE,
    confirmation_date TIMESTAMP,
    confirmation_method VARCHAR(50),
    
    -- File verification
    checksum VARCHAR(255),
    file_size BIGINT,
    
    -- Status tracking
    delivery_status VARCHAR(50),
    -- Status: 'pending', 'delivered', 'confirmed', 'failed', 'bounced'
    
    -- Additional information
    notes TEXT,
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_delivery_status CHECK (delivery_status IN ('pending', 'delivered', 'confirmed', 'failed', 'bounced'))
);

-- Indexes
CREATE INDEX idx_nef_audit_certificate_id ON nef_delivery_audit(certificate_id);
CREATE INDEX idx_nef_audit_employee_id ON nef_delivery_audit(employee_id);
CREATE INDEX idx_nef_audit_delivery_date ON nef_delivery_audit(delivery_date);
CREATE INDEX idx_nef_audit_delivery_status ON nef_delivery_audit(delivery_status);
CREATE INDEX idx_nef_audit_metadata ON nef_delivery_audit USING gin(metadata);

-- Comments
COMMENT ON TABLE nef_delivery_audit IS 'Audit trail for NEF certificate distribution';
COMMENT ON COLUMN nef_delivery_audit.metadata IS 'Additional delivery metadata in JSON format';

-- ============================================================================
-- CERTIFICATE ROTATION HISTORY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS certificate_rotation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Employee information
    employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
    employee_email VARCHAR(255) NOT NULL,
    
    -- Old certificate
    old_certificate_id VARCHAR(255),
    old_issued_at TIMESTAMP,
    old_expires_at TIMESTAMP,
    old_revoked_at TIMESTAMP,
    
    -- New certificate
    new_certificate_id VARCHAR(255),
    new_issued_at TIMESTAMP,
    new_expires_at TIMESTAMP,
    
    -- Rotation details
    rotation_reason VARCHAR(255),
    rotation_type VARCHAR(50),
    -- Types: 'scheduled', 'manual', 'emergency', 'compromise'
    
    -- Metadata
    rotated_by VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_rotation_type CHECK (rotation_type IN ('scheduled', 'manual', 'emergency', 'compromise'))
);

-- Indexes
CREATE INDEX idx_cert_rotation_employee_id ON certificate_rotation_history(employee_id);
CREATE INDEX idx_cert_rotation_created_at ON certificate_rotation_history(created_at);

-- Comments
COMMENT ON TABLE certificate_rotation_history IS 'History of certificate rotations and renewals';

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_vpn_certificates_updated_at
    BEFORE UPDATE ON vpn_certificates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_employees_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_nef_delivery_audit_updated_at
    BEFORE UPDATE ON nef_delivery_audit
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate session duration
CREATE OR REPLACE FUNCTION calculate_vpn_session_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.disconnected_at IS NOT NULL AND NEW.connected_at IS NOT NULL THEN
        NEW.session_duration = NEW.disconnected_at - NEW.connected_at;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for session duration
CREATE TRIGGER calculate_session_duration
    BEFORE INSERT OR UPDATE ON vpn_connection_logs
    FOR EACH ROW
    EXECUTE FUNCTION calculate_vpn_session_duration();

-- Function to auto-expire certificates
CREATE OR REPLACE FUNCTION auto_expire_nef_certificates()
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE vpn_certificates
    SET status = 'expired',
        updated_at = NOW()
    WHERE expires_at < NOW()
    AND status = 'active';
    
    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;

-- Function to increment download count
CREATE OR REPLACE FUNCTION increment_download_count(cert_id VARCHAR)
RETURNS VOID AS $$
BEGIN
    UPDATE vpn_certificates
    SET download_count = download_count + 1,
        last_downloaded_at = NOW()
    WHERE certificate_id = cert_id;
END;
$$ LANGUAGE plpgsql;

-- Function to log connection
CREATE OR REPLACE FUNCTION log_vpn_connection(
    cert_id VARCHAR,
    emp_id UUID,
    client_ip INET
)
RETURNS UUID AS $$
DECLARE
    log_id UUID;
BEGIN
    INSERT INTO vpn_connection_logs (
        id,
        certificate_id,
        employee_id,
        connected_at,
        ip_address,
        status
    ) VALUES (
        gen_random_uuid(),
        cert_id,
        emp_id,
        NOW(),
        client_ip,
        'connected'
    ) RETURNING id INTO log_id;
    
    -- Update certificate last connection
    UPDATE vpn_certificates
    SET last_connection_at = NOW(),
        total_connections = total_connections + 1
    WHERE certificate_id = cert_id;
    
    RETURN log_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active certificates view
CREATE OR REPLACE VIEW vpn_active_nef_certificates AS
SELECT 
    c.id,
    c.employee_id,
    c.employee_name,
    c.employee_email,
    c.certificate_id,
    c.issued_at,
    c.expires_at,
    EXTRACT(DAYS FROM (c.expires_at - NOW())) AS days_until_expiry,
    c.download_count,
    c.last_downloaded_at,
    c.last_connection_at,
    c.total_connections,
    c.config_file
FROM vpn_certificates c
WHERE c.status = 'active'
AND c.expires_at > NOW()
ORDER BY c.expires_at;

-- Expiring soon certificates (30 days)
CREATE OR REPLACE VIEW vpn_expiring_nef_certificates AS
SELECT 
    c.employee_name,
    c.employee_email,
    c.certificate_id,
    c.expires_at,
    EXTRACT(DAYS FROM (c.expires_at - NOW())) AS days_remaining
FROM vpn_certificates c
WHERE c.status = 'active'
AND c.expires_at BETWEEN NOW() AND NOW() + INTERVAL '30 days'
ORDER BY c.expires_at;

-- Recent connections view
CREATE OR REPLACE VIEW vpn_recent_connections AS
SELECT 
    l.id,
    l.certificate_id,
    l.employee_name,
    l.connected_at,
    l.disconnected_at,
    l.session_duration,
    l.ip_address,
    l.bytes_sent + l.bytes_received AS total_bytes,
    l.status
FROM vpn_connection_logs l
ORDER BY l.connected_at DESC
LIMIT 100;

-- Certificate usage statistics
CREATE OR REPLACE VIEW vpn_certificate_usage_stats AS
SELECT 
    c.certificate_id,
    c.employee_name,
    c.employee_email,
    c.download_count,
    c.total_connections,
    c.last_connection_at,
    COUNT(l.id) AS logged_connections,
    SUM(l.bytes_sent + l.bytes_received) AS total_traffic_bytes
FROM vpn_certificates c
LEFT JOIN vpn_connection_logs l ON c.certificate_id = l.certificate_id
WHERE c.status = 'active'
GROUP BY c.id, c.certificate_id, c.employee_name, c.employee_email, 
         c.download_count, c.total_connections, c.last_connection_at
ORDER BY c.total_connections DESC;

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant permissions to tbaps user
GRANT ALL PRIVILEGES ON TABLE employees TO ztuser;
GRANT ALL PRIVILEGES ON TABLE vpn_certificates TO ztuser;
GRANT ALL PRIVILEGES ON TABLE vpn_connection_logs TO ztuser;
GRANT ALL PRIVILEGES ON TABLE nef_delivery_audit TO ztuser;
GRANT ALL PRIVILEGES ON TABLE certificate_rotation_history TO ztuser;

GRANT SELECT ON vpn_active_nef_certificates TO ztuser;
GRANT SELECT ON vpn_expiring_nef_certificates TO ztuser;
GRANT SELECT ON vpn_recent_connections TO ztuser;
GRANT SELECT ON vpn_certificate_usage_stats TO ztuser;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert sample configuration if needed
-- (This would be customized based on deployment)

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON SCHEMA public IS 'TBAPS NEF Certificate Management Database Schema';
