---
name: offensive-active-directory-and-windows
description: Enterprise Active Directory attacks, Kerberos exploitation, privilege escalation, Windows security boundaries, and NetExec post-exploitation.
---

# Active Directory & Windows Penetration Testing Master Suite

Comprehensive AD attack paths, BloodHound analysis, ticket forging, credential harvesting, and domain privilege escalation.

## Modules
### Active Directory (`offensive-active-directory`)
---
name: offensive-active-directory
description: "Active Directory attack methodology for internal network red team engagements. Covers reconnaissance (BloodHound, PowerView, ADExplorer), credential abuse (Kerberoasting, ASREProasting, NTLM relay, LLMNR/NBT-NS poisoning), privilege escalation (ACL abuse, GPO abuse, unconstrained/constrained delegation), lateral movement (Pass-the-Hash, Pass-the-Ticket, Overpass-the-Hash, WMI/WinRM/PsExec), persi

### Lateral Movement (`offensive-lateral-movement`)
---
name: offensive-lateral-movement
description: "Comprehensive lateral movement tradecraft for authorized red team engagements covering credential-based movement (pass-the-hash, pass-the-ticket, overpass-the-hash), NTLM relay attacks (ntlmrelayx with PetitPotam, DFSCoerce, PrinterBug coercion), remote execution protocols (WMI, WinRM, DCOM, PsExec and alternatives), RDP session hijacking, and network pivoting through tunneling tools (chisel, lig

### Netexec (`offensive-netexec`)
---
name: offensive-netexec
description: >
  Use this skill whenever the user asks about NetExec (nxc) — a network
  exploitation and post-exploitation tool for Active Directory environments.
  Triggers include: any mention of 'nxc', 'netexec', 'crackmapexec' successor
  questions, AD enumeration, SMB/LDAP/WinRM/MSSQL/SSH/RDP/VNC/WMI/FTP/NFS
  protocol attacks, password spraying, credential dumping (SAM, NTDS, LSASS,
  DPAPI), Kerberoasting, ASRE

### Windows Boundaries (`offensive-windows-boundaries`)
---
name: offensive-windows-boundaries
description: "Windows security boundary taxonomy and attack surface enumeration: kernel/user boundary, sandbox boundaries (LPAC, AppContainer), COM/RPC boundaries, hypervisor boundary, trust level transitions. Use when planning privilege escalation paths, sandbox escapes, or understanding Windows security architecture."
---

# SKILL: Week 7: Defeating Windows Security Boundaries

## Metadata
- **Skill Name**

### Windows Mitigations (`offensive-windows-mitigations`)
---
name: offensive-windows-mitigations
description: "Deep-dive on Windows exploit mitigations: ASLR, DEP/NX, CFG, CET/Shadow Stack, SEHOP, Heap Guard, ACG, Arbitrary Code Guard. Covers both the protection mechanism and known bypass techniques. Use when researching Windows exploit mitigations, planning bypass strategies, or understanding protection depth."
---

# SKILL: Week 6: Understanding Windows Mitigations

## Metadata
- **Skill Name**: wind

### Windows Privesc (`offensive-windows-privesc`)
---
name: offensive-windows-privesc
description: "Comprehensive Windows privilege escalation methodology for offensive security engagements. Covers the full attack surface from a standard user shell to NT AUTHORITY\\SYSTEM: token impersonation via SeImpersonate and SeAssignPrimaryToken privileges using JuicyPotato, PrintSpoofer, GodPotato, SweetPotato, and RoguePotato; service misconfigurations including unquoted service paths, weak service DACLs

