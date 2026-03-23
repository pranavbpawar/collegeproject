-- ============================================================================
-- TBAPS VPN Infrastructure - Database Schema
-- 
-- Tables for managing VPN certificates, connections, and audit logs
-- GDPR compliant with data retention policies
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- VPN CERTIFICATES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS vpn_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Employee information
    employee_id VARCHAR(255) UNIQUE NOT NULL,
    employee_name VARCHAR(255) NOT NULL,
    employee_email VARCHAR(255) NOT NULL,
    
    -- Certificate details
    certificate_name VARCHAR(255) UNIQUE NOT NULL,
    certificate_serial VARCHAR(255),
    
    -- Lifecycle
    issued_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    revocation_reason TEXT,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    -- Status values: 'active', 'revoked', 'expired', 'suspended'
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    
    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('active', 'revoked', 'expired', 'suspended')),
    CONSTRAINT valid_dates CHECK (expires_at > issued_at)
);

-- Indexes
CREATE INDEX idx_vpn_certs_employee_id ON vpn_certificates(employee_id);
CREATE INDEX idx_vpn_certs_status ON vpn_certificates(status);
CREATE INDEX idx_vpn_certs_expires_at ON vpn_certificates(expires_at);

-- Comments
COMMENT ON TABLE vpn_certificates IS 'VPN client certificates for employee access';
COMMENT ON COLUMN vpn_certificates.status IS 'Certificate status: active, revoked, expired, suspended';

-- ============================================================================
-- VPN CONNECTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS vpn_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Employee and certificate
    employee_id VARCHAR(255) NOT NULL,
    certificate_name VARCHAR(255) NOT NULL,
    
    -- Connection details
    connected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    disconnected_at TIMESTAMP,
    disconnect_reason VARCHAR(255),
    
    -- Network information
    client_ip_address INET,
    vpn_ip_address INET,
    server_ip_address INET,
    
    -- Traffic statistics
    bytes_received BIGINT DEFAULT 0,
    bytes_sent BIGINT DEFAULT 0,
    packets_received BIGINT DEFAULT 0,
    packets_sent BIGINT DEFAULT 0,
    
    -- Session information
    session_duration_seconds INTEGER,
    connection_protocol VARCHAR(10), -- 'udp' or 'tcp'
    cipher VARCHAR(50),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Foreign key
    FOREIGN KEY (employee_id) REFERENCES vpn_certificates(employee_id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT valid_connection_dates CHECK (
        disconnected_at IS NULL OR disconnected_at >= connected_at
    )
);

-- Indexes
CREATE INDEX idx_vpn_conn_employee_id ON vpn_connections(employee_id);
CREATE INDEX idx_vpn_conn_connected_at ON vpn_connections(connected_at);
CREATE INDEX idx_vpn_conn_active ON vpn_connections(disconnected_at) WHERE disconnected_at IS NULL;

-- Comments
COMMENT ON TABLE vpn_connections IS 'VPN connection logs for access tracking and auditing';
COMMENT ON COLUMN vpn_connections.session_duration_seconds IS 'Calculated: disconnected_at - connected_at';

-- ============================================================================
-- VPN AUDIT LOG TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS vpn_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event information
    event_type VARCHAR(100) NOT NULL,
    -- Event types: 'certificate_issued', 'certificate_revoked', 'connection_established',
    --              'connection_terminated', 'authentication_failed', 'configuration_changed'
    
    -- Related entities
    employee_id VARCHAR(255),
    certificate_name VARCHAR(255),
    
    -- Event details
    details JSONB,
    severity VARCHAR(20) DEFAULT 'info',
    -- Severity: 'info', 'warning', 'error', 'critical'
    
    -- Source
    source_ip INET,
    user_agent TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_severity CHECK (severity IN ('info', 'warning', 'error', 'critical'))
);

-- Indexes
CREATE INDEX idx_vpn_audit_event_type ON vpn_audit_log(event_type);
CREATE INDEX idx_vpn_audit_employee_id ON vpn_audit_log(employee_id);
CREATE INDEX idx_vpn_audit_created_at ON vpn_audit_log(created_at);
CREATE INDEX idx_vpn_audit_severity ON vpn_audit_log(severity);
CREATE INDEX idx_vpn_audit_details ON vpn_audit_log USING gin(details);

-- Comments
COMMENT ON TABLE vpn_audit_log IS 'Comprehensive audit log for all VPN-related events';
COMMENT ON COLUMN vpn_audit_log.details IS 'JSON object with event-specific details';

-- ============================================================================
-- VPN STATISTICS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS vpn_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Time period
    date DATE NOT NULL,
    hour INTEGER,
    
    -- Metrics
    total_connections INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    total_bytes_transferred BIGINT DEFAULT 0,
    average_session_duration_seconds INTEGER DEFAULT 0,
    
    -- Peak metrics
    peak_concurrent_connections INTEGER DEFAULT 0,
    peak_bandwidth_mbps NUMERIC(10, 2) DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_hour CHECK (hour IS NULL OR (hour >= 0 AND hour <= 23)),
    UNIQUE (date, hour)
);

-- Indexes
CREATE INDEX idx_vpn_stats_date ON vpn_statistics(date);
CREATE INDEX idx_vpn_stats_date_hour ON vpn_statistics(date, hour);

-- Comments
COMMENT ON TABLE vpn_statistics IS 'Aggregated VPN usage statistics for monitoring and reporting';

-- ============================================================================
-- VPN CONFIGURATION TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS vpn_configuration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Configuration key-value
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR(50) NOT NULL, -- 'string', 'integer', 'boolean', 'json'
    
    -- Metadata
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    
    -- Versioning
    version INTEGER DEFAULT 1,
    previous_value TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(255)
);

-- Indexes
CREATE INDEX idx_vpn_config_key ON vpn_configuration(config_key);

-- Comments
COMMENT ON TABLE vpn_configuration IS 'VPN server configuration settings';
COMMENT ON COLUMN vpn_configuration.is_sensitive IS 'If true, value should be encrypted at rest';

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

-- Trigger for vpn_certificates
CREATE TRIGGER update_vpn_certificates_updated_at
    BEFORE UPDATE ON vpn_certificates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for vpn_statistics
CREATE TRIGGER update_vpn_statistics_updated_at
    BEFORE UPDATE ON vpn_statistics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for vpn_configuration
CREATE TRIGGER update_vpn_configuration_updated_at
    BEFORE UPDATE ON vpn_configuration
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate session duration
CREATE OR REPLACE FUNCTION calculate_session_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.disconnected_at IS NOT NULL AND NEW.connected_at IS NOT NULL THEN
        NEW.session_duration_seconds = EXTRACT(EPOCH FROM (NEW.disconnected_at - NEW.connected_at))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for session duration calculation
CREATE TRIGGER calculate_vpn_session_duration
    BEFORE INSERT OR UPDATE ON vpn_connections
    FOR EACH ROW
    EXECUTE FUNCTION calculate_session_duration();

-- Function to auto-expire certificates
CREATE OR REPLACE FUNCTION auto_expire_certificates()
RETURNS void AS $$
BEGIN
    UPDATE vpn_certificates
    SET status = 'expired',
        updated_at = NOW()
    WHERE expires_at < NOW()
    AND status = 'active';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active certificates view
CREATE OR REPLACE VIEW vpn_active_certificates AS
SELECT 
    employee_id,
    employee_name,
    employee_email,
    certificate_name,
    issued_at,
    expires_at,
    EXTRACT(DAYS FROM (expires_at - NOW())) AS days_until_expiry
FROM vpn_certificates
WHERE status = 'active'
AND expires_at > NOW()
ORDER BY expires_at;

-- Active connections view
CREATE OR REPLACE VIEW vpn_active_connections AS
SELECT 
    c.id,
    c.employee_id,
    cert.employee_name,
    c.certificate_name,
    c.connected_at,
    c.client_ip_address,
    c.vpn_ip_address,
    EXTRACT(EPOCH FROM (NOW() - c.connected_at))::INTEGER AS session_duration_seconds,
    c.bytes_received,
    c.bytes_sent
FROM vpn_connections c
JOIN vpn_certificates cert ON c.employee_id = cert.employee_id
WHERE c.disconnected_at IS NULL
ORDER BY c.connected_at DESC;

-- Connection history view
CREATE OR REPLACE VIEW vpn_connection_history AS
SELECT 
    c.id,
    c.employee_id,
    cert.employee_name,
    c.connected_at,
    c.disconnected_at,
    c.session_duration_seconds,
    c.bytes_received + c.bytes_sent AS total_bytes,
    c.client_ip_address,
    c.vpn_ip_address
FROM vpn_connections c
JOIN vpn_certificates cert ON c.employee_id = cert.employee_id
ORDER BY c.connected_at DESC;

-- ============================================================================
-- INITIAL CONFIGURATION
-- ============================================================================

-- Insert default configuration
INSERT INTO vpn_configuration (config_key, config_value, config_type, description) VALUES
    ('server_ip', 'YOUR_SERVER_IP', 'string', 'OpenVPN server public IP address'),
    ('server_port', '1194', 'integer', 'OpenVPN server port'),
    ('protocol', 'udp', 'string', 'Connection protocol (udp or tcp)'),
    ('cipher', 'AES-256-CBC', 'string', 'Encryption cipher'),
    ('auth', 'SHA256', 'string', 'Authentication algorithm'),
    ('max_clients', '500', 'integer', 'Maximum concurrent clients'),
    ('cert_validity_days', '365', 'integer', 'Certificate validity period in days'),
    ('ca_validity_days', '3650', 'integer', 'CA certificate validity period in days'),
    ('log_retention_days', '90', 'integer', 'Connection log retention period'),
    ('audit_retention_days', '365', 'integer', 'Audit log retention period')
ON CONFLICT (config_key) DO NOTHING;

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant permissions to tbaps user
GRANT ALL PRIVILEGES ON TABLE vpn_certificates TO ztuser;
GRANT ALL PRIVILEGES ON TABLE vpn_connections TO ztuser;
GRANT ALL PRIVILEGES ON TABLE vpn_audit_log TO ztuser;
GRANT ALL PRIVILEGES ON TABLE vpn_statistics TO ztuser;
GRANT ALL PRIVILEGES ON TABLE vpn_configuration TO ztuser;

GRANT SELECT ON vpn_active_certificates TO ztuser;
GRANT SELECT ON vpn_active_connections TO ztuser;
GRANT SELECT ON vpn_connection_history TO ztuser;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON SCHEMA public IS 'TBAPS VPN Infrastructure Database Schema';
