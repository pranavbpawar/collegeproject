FROM python:3.11-slim

LABEL maintainer="TBAPS Infrastructure Team"
LABEL description="VPN Connection Logger Service"

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    asyncpg==0.29.0 \
    python-dotenv==1.0.0

# Copy application
COPY vpn_logger.py /app/

# Create log directory
RUN mkdir -p /var/log

# Run as non-root user
RUN useradd -m -u 1000 vpnlogger && \
    chown -R vpnlogger:vpnlogger /app /var/log

USER vpnlogger

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/var/log/vpn-logger.log') else 1)"

# Run logger
CMD ["python", "-u", "vpn_logger.py"]
