---
name: web-penetration-testing-suite
description: Comprehensive offensive web application security and penetration testing master suite covering OWASP Top 10, API abuse, injection flaws, deserialization, auth bypass, and modern web vulnerabilities.
---

# Web Application Penetration Testing Master Suite

Industrial-grade web security testing guidelines, vulnerability classes, validation methodologies, and proof-of-concept patterns.

## Attack Vectors & Vulnerability Classes
### Api Abuse (`offensive-api-abuse`)
---
name: offensive-api-abuse
description: "Advanced API exploitation methodology focused on business logic abuse and sophisticated attack patterns that bypass traditional security controls. Covers business logic bypass through API call chaining and workflow manipulation. Addresses GraphQL-specific attacks including batching for credential brute-force, query depth exploitation, and introspection abuse. Includes pagination exploitation for data ex

### Api Security (`offensive-api-security`)
---
name: offensive-api-security
description: "Comprehensive API security testing methodology covering REST, gRPC, and WebSocket attack surfaces. Addresses the full OWASP API Security Top 10 2023 including BOLA/IDOR, broken authentication, excessive data exposure, rate limiting bypass, BFLA, mass assignment, SSRF, and security misconfiguration. Includes REST-specific attacks such as HTTP verb tampering, content-type switching, and parameter pollu

### Business Logic (`offensive-business-logic`)
---
name: offensive-business-logic
description: "Business logic vulnerability testing for web/mobile/API engagements. Covers workflow bypass, state machine violations, multi-step process abuse, price/quantity/discount manipulation, currency confusion, coupon stacking, refund/chargeback abuse, race conditions on logic boundaries, parameter tampering for hidden flows, role/tenant boundary violations, time-of-check vs use, anti-automation defeat, fr

### C2 Frameworks (`offensive-c2-frameworks`)
---
name: offensive-c2-frameworks
description: "Command and Control framework deployment, configuration, and operational tradecraft for red team engagements. Covers Cobalt Strike (malleable C2 profiles, Beacon types HTTP/HTTPS/DNS/SMB, Beacon Object Files for in-memory execution, sleep and jitter tuning, named pipe pivoting), Sliver (implant generation across mTLS/WireGuard/DNS transport, operator multiplayer mode, armory extensions), Mythic (age

### Crypto Attacks (`offensive-crypto-attacks`)
---
name: offensive-crypto-attacks
description: "Systematic methodology for identifying and exploiting cryptographic implementation weaknesses in real-world applications. Covers padding oracle attacks against CBC-mode ciphers with PKCS7 padding (Vaudenay's original attack through modern padbuster automation), ECB mode exploitation including block cut-and-paste and byte-at-a-time decryption, hash length extension attacks against SHA1/SHA256/MD5-ba

### Data Exfiltration (`offensive-data-exfiltration`)
---
name: offensive-data-exfiltration
description: "Dense methodology covering DNS exfiltration (dnscat2, iodine, dns2tcp), HTTPS tunneling (domain fronting, CDN abuse, legitimate service channels), ICMP tunneling (icmpsh, ptunnel-ng), cloud storage dead drops (S3 presigned URLs, Azure Blob SAS tokens, GCS signed URLs), email-based exfil (SMTP, EWS, draft method), steganography (image, audio, document metadata), encoding/encryption (base64 chunki

### Deserialization (`offensive-deserialization`)
---
name: offensive-deserialization
description: "Insecure deserialization exploitation across Java, PHP, .NET, Python, Node.js, and Ruby. Covers gadget chain construction with ysoserial/phpggc/ysoserial.net, ObjectInputStream and BinaryFormatter sink identification, pickle __reduce__ RCE, phar:// wrapper abuse, Jackson polymorphic typing, Json.NET TypeNameHandling, ViewState tampering, node-serialize IIFE injection, Ruby Marshal.load and YAML.lo

### File Upload (`offensive-file-upload`)
---
name: offensive-file-upload
description: "File upload vulnerability checklist: MIME type bypass, extension bypass, magic byte manipulation, path traversal in filenames, stored XSS via SVG/HTML upload, server-side processing attacks, and race conditions. Use for assessing file upload endpoints in web app pentests or bug bounty."
---

# SKILL: File Upload Vulnerabilities

## Metadata
- **Skill Name**: file-upload
- **Folder**: offensive-file-up

### Graphql (`offensive-graphql`)
---
name: offensive-graphql
description: "Offensive methodology for attacking GraphQL APIs during penetration tests and bug bounty engagements. Covers the full attack lifecycle: endpoint discovery, introspection abuse and blind schema reconstruction when introspection is disabled, authentication and authorization bypass through Relay node IDs and nested object traversal, injection via variables and directives, query batching for brute force and O

### Idor (`offensive-idor`)
---
name: offensive-idor
description: "IDOR (Insecure Direct Object Reference) testing checklist: object ID enumeration, horizontal/vertical privilege escalation, GUID predictability, indirect references via hashes, chained IDOR, and API endpoint IDOR. Use for web app pentests and bug bounty IDOR discovery."
---

# SKILL: Insecure Direct Object References (IDOR)

## Metadata
- **Skill Name**: idor
- **Folder**: offensive-idor
- **Source**: https:

### Jwt (`offensive-jwt`)
---
name: offensive-jwt
description: "JWT attack methodology for penetration testers. Covers algorithm confusion (alg:none, RS256→HS256), weak HMAC secret brute force, kid parameter injection (SQLi, path traversal), jku/x5u/jwk header injection, JWKS cache poisoning, JWS/JWE confusion, timing attacks, and mobile JWT storage extraction. Use when testing JWT-based authentication, hunting auth bypass via token manipulation, or evaluating JWT impleme

### Oauth (`offensive-oauth`)
---
name: offensive-oauth
description: "OAuth 2.0 attack checklist: authorization code interception, redirect_uri bypass, CSRF on OAuth flow, state parameter abuse, open redirector chaining, token leakage via Referer, PKCE bypass, and scope escalation. Use when testing OAuth implementations in web apps or bug bounty."
---

# SKILL: OAuth Security Testing

## Metadata
- **Skill Name**: oauth-attacks
- **Folder**: offensive-oauth
- **Source**: http

### Open Redirect (`offensive-open-redirect`)
---
name: offensive-open-redirect
description: "Open redirect vulnerability checklist: parameter identification, bypass techniques (URL encoding, double slashes, CRLF injection, protocol handlers), chaining with OAuth/SSRF, and impact escalation paths. Use for web app testing and bug bounty open redirect discovery."
---

# SKILL: Open Redirect Vulnerabilities

## Metadata
- **Skill Name**: open-redirect
- **Folder**: offensive-open-redirect
- **S

### Parameter Pollution (`offensive-parameter-pollution`)
---
name: offensive-parameter-pollution
description: "HTTP parameter pollution (HPP) checklist: duplicate parameter injection, backend vs frontend parsing differences, WAF bypass via HPP, server-side vs client-side HPP, and practical exploitation patterns. Use when testing web applications for parameter handling flaws."
---

# SKILL: HTTP Parameter Pollution (HPP)

## Metadata
- **Skill Name**: parameter-pollution
- **Folder**: offensive-paramete

### Race Condition (`offensive-race-condition`)
---
name: offensive-race-condition
description: "Race condition (TOCTOU) testing checklist: identifying timing windows, Burp Suite Turbo Intruder, Last-Byte sync technique, rate limit bypass, double-spend attacks, and concurrent request exploitation. Use for web app race condition testing or bug bounty time-of-check-to-time-of-use bugs."
---

# SKILL: Race Conditions

## Metadata
- **Skill Name**: race-condition
- **Folder**: offensive-race-condi

### Rce (`offensive-rce`)
---
name: offensive-rce
description: "Remote Code Execution testing checklist: OS command injection, SSTI-to-RCE, deserialization RCE, file upload RCE, XXE with SSRF to RCE, RCE via dependency confusion, and CVE-based RCE patterns. Use for web app pentests and bug bounty RCE discovery."
---

# SKILL: Remote Code Execution

## Metadata
- **Skill Name**: rce
- **Folder**: offensive-rce
- **Source**: https://github.com/SnailSploit/offensive-checklis

### Request Smuggling (`offensive-request-smuggling`)
---
name: offensive-request-smuggling
description: "HTTP request smuggling checklist: CL.TE, TE.CL, TE.TE variants, detection with timing and differential responses, WAF bypass, cache poisoning, credential hijacking, and request smuggling via HTTP/2. Use when testing reverse proxy/load balancer configurations."
---

# SKILL: HTTP Request Smuggling

## Metadata
- **Skill Name**: request-smuggling
- **Folder**: offensive-request-smuggling
- **Sourc

### Sqli (`offensive-sqli`)
---
name: offensive-sqli
description: "SQL injection testing skill for offensive security assessments and bug bounty hunting. Covers error-based, UNION-based, boolean/time-based blind, out-of-band, second-order, NoSQL, GraphQL, WebSocket, and JSON-operator SQLi. Includes WAF bypass techniques, database-specific exploitation (MySQL, MSSQL, PostgreSQL, Oracle), cloud-native attack paths, ORM CVE tracking, and SQLmap automation. Use when performing 

### Ssrf (`offensive-ssrf`)
---
name: offensive-ssrf
description: "Server-Side Request Forgery testing checklist: SSRF discovery, blind SSRF with out-of-band, cloud metadata endpoints (AWS/GCP/Azure), SSRF filter bypass techniques (IP encoding, DNS rebinding, redirect chains), and SSRF to RCE escalation. Use for web app SSRF testing and bug bounty."
---

# SKILL: Server-Side Request Forgery (SSRF)

## Metadata
- **Skill Name**: ssrf
- **Folder**: offensive-ssrf
- **Source**

### Ssti (`offensive-ssti`)
---
name: offensive-ssti
description: "Dense description covering Server-Side Template Injection across Jinja2, Twig, Freemarker, Velocity, Pebble, Smarty, Mako, Handlebars, ERB, Thymeleaf, EJS, Pug. Engine fingerprinting, filter bypass, blind exploitation, WAF evasion, SSTI-to-RCE chains. Tools: tplmap. CWE-1336. MITRE T1190. Use when testing template rendering endpoints or exploiting template injection for code execution."
---

# Server-Side Te

### Toctou (`offensive-toctou`)
---
name: offensive-toctou
description: "Time-of-Check / Time-of-Use (TOCTOU) race condition exploitation methodology across binary, kernel, filesystem, web, and container layers. Covers symbolic-link races (open/access/stat split), file-descriptor races, fopen/realpath traversal races, /proc and procfs races, FUSE-backed slow-fs races to widen the window, ptrace and signal races, kernel double-fetch / userspace pointer races, container/runc/syml

### Vuln Classes (`offensive-vuln-classes`)
---
name: offensive-vuln-classes
description: "Exploit development curriculum covering core vulnerability classes with real-world CVE case studies: stack/heap buffer overflows, use-after-free, integer overflows, format strings, type confusion, and race conditions. Use when learning or teaching vuln classes, researching specific CVE patterns, or building exploit dev knowledge."
---

# SKILL: Week 1: Vulnerability Classes with Real-World Examples



### Waf Bypass (`offensive-waf-bypass`)
---
name: offensive-waf-bypass
description: "WAF bypass techniques checklist: encoding bypass (URL/HTML/Unicode/double encoding), case variation, comment injection, HTTP header manipulation, chunked encoding, IP rotation, timing attacks, and payload obfuscation per WAF vendor. Use when WAF is blocking payloads during web app tests."
---

# SKILL: WAF Bypass Techniques

## Metadata
- **Skill Name**: waf-bypass
- **Folder**: offensive-waf-bypass
- 

### Xss (`offensive-xss`)
---
name: offensive-xss
description: "Cross-Site Scripting testing checklist: stored/reflected/DOM/blind XSS discovery, polyglot payloads, CSP bypass, XSS filter bypass, event handler injection, DOM clobbering, mutation XSS, and impact escalation (session hijack, phishing, keylogging). Use for web app XSS testing and bug bounty."
---

# SKILL: Cross-Site Scripting (XSS)

## Metadata
- **Skill Name**: xss
- **Folder**: offensive-xss
- **Source**: 

### Xxe (`offensive-xxe`)
---
name: offensive-xxe
description: "XML External Entity injection testing checklist: classic XXE, blind XXE (out-of-band), XXE via file upload (SVG/docx), XXE in SOAP/REST, error-based XXE, XInclude attacks, and XXE filter bypass. Use for web app XXE testing and bug bounty."
---

# SKILL: XML External Entity (XXE) Injection

## Metadata
- **Skill Name**: xxe
- **Folder**: offensive-xxe
- **Source**: https://github.com/SnailSploit/offensive-chec

