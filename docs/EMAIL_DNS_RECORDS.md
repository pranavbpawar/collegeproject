# Self-Hosted Email DNS Records Guide

If you are using Postfix to send emails directly from your server instead of a service like SendGrid, you **must** configure these four DNS records on your Domain Name Registrar (e.g., Cloudflare, GoDaddy, Namecheap). 

If you skip these, Google, Yahoo, and Microsoft will automatically drop your emails or send them straight to the Spam folder.

> **Note:** In these examples, we assume your application is running on `tbaps.yourdomain.com` and your server's IP is `123.45.67.89`. Replace these with your actual domain and IP.

---

## 1. Reverse DNS (PTR Record)
This cannot usually be set in your Domain Registrar. You must set this in your **Hosting Provider's Dashboard** (e.g., DigitalOcean, Hetzner, AWS, Linode).

You need to tell your hosting provider that the IP address `123.45.67.89` reverse-resolves to `tbaps.yourdomain.com`. 
- **DigitalOcean:** Automatically sets this based on the droplet's given name.
- **Hetzner:** Under your Server → IP → Reverse DNS.

## 2. A Record & MX Record
You must have an A record pointing to your server, and an MX (Mail Exchange) record telling the world that this server handles mail for the subdomain.

| Type | Name | Value | Priority |
| :--- | :--- | :--- | :--- |
| **A** | `tbaps` | `123.45.67.89` | N/A |
| **MX** | `tbaps` | `tbaps.yourdomain.com` | `10` |

## 3. SPF Record (Sender Policy Framework)
This tells the world that only your exact IP address is allowed to send emails that claim to be from `@tbaps.yourdomain.com`.

| Type | Name | Value |
| :--- | :--- | :--- |
| **TXT** | `tbaps` | `v=spf1 mx a ip4:123.45.67.89 -all` |

> *The `-all` at the end strictly forbids any other IP address from sending emails on your behalf.*

## 4. DKIM Record (DomainKeys Identified Mail)
This is a cryptographic public key. Postfix will sign every email intimately using a private key, and Gmail will check this DNS record to verify the signature.

You **must run `sudo bash scripts/setup-postfix.sh` first** to generate this key! The script will print the exact value you need to paste.

| Type | Name | Value |
| :--- | :--- | :--- |
| **TXT** | `default._domainkey.tbaps` | *`v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0... (Wait for script output)`* |

## 5. DMARC Record
This tells Gmail and Yahoo what to do if an email fails the SPF or DKIM checks. 

| Type | Name | Value |
| :--- | :--- | :--- |
| **TXT** | `_dmarc.tbaps` | `v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s;` |

> *The `p=reject` policy means "If anyone else tries to spoof an email from my domain, reject it entirely."*

---

## 🚀 How to Verify It Works

1. Once your DNS records are added (they can take 15 mins to propagate).
2. Go to **[Mail-Tester.com](https://www.mail-tester.com/)**, copy the random email address they give you.
3. Use your application to send a test email to that exact address (e.g., by triggering the "Send Agent" action).
4. Refresh Mail-Tester. If you configured everything perfectly, you will get a **10/10 Score**. If you missed a DNS record, it will tell you exactly which one failed.
