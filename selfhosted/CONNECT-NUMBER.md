# Connecting an existing mobile number to the assistant

A normal consumer mobile SIM lives on the carrier's GSM network and **cannot plug
directly into Asterisk/SIP**. You bridge it one of these ways.

## Option A — Call forwarding to a VoIP DID (easiest, no hardware)
```
Caller -> your mobile -> (forward) -> VoIP DID -> Asterisk -> AI
```
1. Buy a SIP-capable **DID** from a VoIP provider (a **local** DID keeps forwarding cheap).
2. Connect that DID to Asterisk: uncomment the **SIP TRUNK** block in `asterisk/pjsip.conf`,
   fill in the provider's host/username/password, then
   `docker compose exec asterisk asterisk -rx "pjsip reload"`.
3. Add the DID under **Phone Numbers** in the dashboard.
4. On your mobile, enable **call forwarding** to the VoIP number
   (all calls: dial `**21*<VoIP_NUMBER>#`).

Pros: keep your existing number, zero hardware.
Cons: the carrier charges for the forwarded leg (use a local DID to minimise this).

## Option B — GSM gateway / GoIP (use the real SIM) — recommended long term
```
SIM card -> GoIP gateway (hardware) -> SIP -> Asterisk -> AI
```
1. Get a GoIP/Yeastar/Dinstar GSM gateway and insert your SIM (good signal needed).
2. In the GoIP web UI, set the SIP/VoIP server to `YOUR_DROPLET_IP:5060` and register
   as user `goip` with a password.
3. In `asterisk/pjsip.conf`, uncomment the **GSM GATEWAY (GoIP)** block, set the same
   password, then `pjsip reload`.
4. Incoming GSM calls now arrive in context `ai` and reach the assistant (extension `1000`
   / the `_X.` route). Confirm with `asterisk -rx "pjsip show endpoints"` (goip = Available).

Pros: uses the actual SIM/number, no per-call forwarding fees.
Cons: hardware + must stay online with signal; some carriers throttle gateway SIMs.

## Option C — Android bridge app (experimental only)
A spare Android + SIM + a GSM↔SIP bridge app. Unreliable; fine for experiments, not production.

## Not possible: porting a +94 mobile number to an international VoIP provider.

## Firewall reminder
Open `5060/udp` and `10000-10100/udp` so the trunk/gateway can reach Asterisk
(`bash scripts/firewall.sh`), and open them in any DigitalOcean Cloud Firewall too.
