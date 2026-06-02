# Connecting an existing mobile number to the assistant

A normal consumer mobile SIM lives on the carrier's GSM network and **cannot plug
directly into Asterisk/SIP**. You bridge it one of these ways.

## Connecting a SIP DID — self-service (no manual config editing)

You manage everything from the dashboard, then run one command:

1. Buy a SIP **DID + trunk** from a VoIP provider.
2. Dashboard → **SIP Providers** → add it:
   - registration trunk → fill host + username + password
   - IP-based trunk → fill host only, and give the provider your server's IP
3. Dashboard → **Phone Numbers** → add the DID (so calls map to the right company).
4. On the server, apply it:
   ```bash
   bash selfhosted/scripts/apply-trunks.sh
   ```
   This generates `asterisk-generated/pjsip_trunks.conf` from your providers and reloads
   Asterisk. Verify: `docker compose exec asterisk asterisk -rx "pjsip show registrations"`.
5. Call the DID — the assistant answers. Done.

> The `_X.` inbound route already sends any dialed DID to the assistant, so there is no
> dialplan to edit. (A commented manual trunk template also remains in `pjsip.conf` for reference.)

## Option A — Call forwarding to a VoIP DID (use an existing mobile, no hardware)
```
Caller -> your mobile -> (forward) -> VoIP DID -> Asterisk -> AI
```
1. Connect a VoIP DID using the self-service steps above (a **local** DID keeps forwarding cheap).
2. On your mobile, enable **call forwarding** to that VoIP number
   (all calls: dial `**21*<VoIP_NUMBER>#`).

Pros: keep your existing number, zero hardware.
Cons: the carrier charges for the forwarded leg (use a local DID to minimise this).

## Option B — GSM gateway / GoIP (use a real Sri Lankan SIM) — recommended
```
SIM card -> GoIP gateway (hardware) -> SIP -> Asterisk -> AI
```
Now self-service from the dashboard — no manual pjsip editing:
1. Get a GoIP/Yeastar/Dinstar GSM gateway and insert your SIM (good signal needed).
2. Dashboard → **SIP Providers** → Add → type **GSM gateway / GoIP**; set a username
   (e.g. `goip`) and a password.
3. On the server: `bash selfhosted/scripts/apply-trunks.sh` (generates the endpoint + reloads).
4. In the GoIP web UI, set the SIP/VoIP **server = `YOUR_DROPLET_IP:5060`** and register
   with the same username/password.
5. Confirm: `docker compose exec asterisk asterisk -rx "pjsip show endpoints"` → the gateway
   shows **Available**. Incoming GSM calls reach the assistant via context `ai`.

Pros: uses the actual SIM/number, no per-call forwarding fees.
Cons: hardware + must stay online with signal; some carriers throttle gateway SIMs.

## Option C — Android bridge app (experimental only)
A spare Android + SIM + a GSM↔SIP bridge app. Unreliable; fine for experiments, not production.

## Not possible: porting a +94 mobile number to an international VoIP provider.

## Firewall reminder
Open `5060/udp` and `10000-10100/udp` so the trunk/gateway can reach Asterisk
(`bash scripts/firewall.sh`), and open them in any DigitalOcean Cloud Firewall too.
