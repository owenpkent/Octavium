# Octavium Distribution & Monetization Strategy

> **Goal:** Get to revenue quickly with a signed, professional Windows application.
> Octavium is open-source (MIT) — monetization comes from convenience, trust, and value-added distribution.

---

## Revenue Channels

### 1. Gumroad — Primary Sales Channel

**Why Gumroad:** Zero upfront cost, instant setup, handles payments globally, supports pay-what-you-want pricing, and is trusted by indie creators. No approval process — you can be selling within an hour.

**Product Listing:**

| Field | Value |
|-------|-------|
| **Product Name** | Octavium — MIDI Chord Toolkit for Musicians |
| **Tagline** | Making music accessible |
| **Price Model** | Pay-what-you-want, $9 minimum (suggested $19) |
| **URL** | `https://okstudio.gumroad.com/l/octavium` |
| **Delivery** | Digital download — signed `OctaviumSetup-1.1.1.exe` |

**What the buyer gets:**
- EV code-signed Windows installer (no SmartScreen warnings)
- Bundled MIDI chord library (15,000+ chord voicings)
- Free updates for the current major version
- Priority support via email

**Product Description (draft):**
> Octavium is a MIDI chord toolkit that makes music theory accessible. Generate chord progressions, explore voicings across every key and mode, and send chords to your DAW in real-time via MIDI.
>
> **Features:**
> - 🎹 Interactive chord grid with 16 simultaneous voicings
> - 🎵 Algorithmic + MIDI library autofill (15,000+ real chord voicings)
> - 🔀 Smart regeneration with lock, scale compliance, and voice-leading
> - 🎛️ Humanize/drift for natural-sounding playback
> - 🖥️ Works with any DAW via virtual MIDI (loopMIDI, IAC Driver)
>
> **Included:** Signed Windows installer, MIDI chord library, free updates.
>
> Open-source on GitHub — pay for the convenience of a signed, ready-to-run installer with the full chord library bundled.

**Gumroad Setup Steps:**
1. Create account at [gumroad.com](https://gumroad.com) (use OK Studio Inc. email)
2. Connect Stripe or PayPal for payouts
3. Create product → Digital Product
4. Upload `OctaviumSetup-1.1.1.exe` as the deliverable
5. Set pricing: Pay-what-you-want, $9 minimum, $19 suggested
6. Add product images (use Octavium screenshots + logo)
7. Add a short demo video or GIF showing the chord pad in action
8. Set up a custom URL slug: `/l/octavium`
9. Publish and share the link

**Gumroad Tips:**
- Enable **"Offer a free trial"** — lets users download a free unsigned version, then upsell the signed installer
- Use **discount codes** for launch (e.g., `LAUNCH50` for 50% off first week)
- Enable **ratings and reviews** to build social proof
- Set up a **Gumroad Workflow** to send a welcome email with getting-started tips
- Add an **upsell** later (e.g., premium chord packs, additional MIDI libraries)

---

### 2. GitHub Sponsors — Recurring Revenue

**Why:** People who use the open-source version may want to support development. GitHub Sponsors has zero fees — 100% of the money goes to you.

**Setup:**
1. Go to [github.com/sponsors](https://github.com/sponsors) and enroll your account
2. Create tiers:

| Tier | Price | Perks |
|------|-------|-------|
| ☕ **Supporter** | $3/month | Name in SUPPORTERS.md, sponsor badge |
| 🎵 **Musician** | $9/month | Above + early access to new features, beta builds |
| 🎹 **Studio** | $29/month | Above + priority feature requests, direct support channel |
| 🏢 **Sponsor** | $99/month | Above + logo in README, consultation on custom features |

3. Add a `FUNDING.yml` to enable the "Sponsor" button on your repo

**One-time sponsorship:** Also enable one-time donations ($5, $15, $50, $100) for people who prefer a single contribution over a subscription.

---

### 3. GitHub Releases — Free + Paid Tiers

Use GitHub Releases for the **free open-source version** (unsigned exe, no MIDI library). This drives traffic to Gumroad for the premium signed installer.

**Release strategy:**
- **GitHub Release** (free): Unsigned `Octavium.exe` standalone — users build from source or download the raw exe. No MIDI library included. May trigger SmartScreen warning.
- **Gumroad** (paid): Signed `OctaviumSetup-1.1.1.exe` installer with bundled MIDI library, no SmartScreen warnings, professional install experience.

This is the **open-core** model: the software is fully open-source and free, but the *convenience* of a signed, bundled, installer is worth paying for.

---

### 4. Ko-fi — Tips & One-Time Support

**Why:** Lower friction than GitHub Sponsors for non-developers. Musicians are used to Ko-fi.

**Setup:**
1. Create a [Ko-fi](https://ko-fi.com) page for OK Studio
2. Link it from the README and the application's Help/About dialog
3. Accept one-time "coffees" ($3–5 each) and commissions

---

### 5. itch.io — Indie Software Marketplace

**Why:** itch.io has a large creative/indie community. Musicians and game developers browse it for tools. Supports pay-what-you-want and "name your own price" models.

**Setup:**
1. Create a project at [itch.io](https://itch.io)
2. Upload the signed installer
3. Categorize as: **Tool → Music**
4. Set pricing: Name your own price, $0 minimum (or $5+)
5. Add screenshots and a demo GIF

---

### 6. Future Channels (Lower Priority)

| Channel | Notes |
|---------|-------|
| **Microsoft Store** | Higher trust, wider reach, but 15% fee and lengthy review process |
| **YouTube demos** | Tutorial/demo videos drive organic traffic to Gumroad |
| **Reddit / Discord** | r/WeAreTheMusicMakers, r/midi, r/musicproduction — share free version, link to paid |
| **Music production blogs** | Reach out to BedroomProducersBlog, Rekkerd, Plugin Boutique |
| **Patreon** | Alternative to GitHub Sponsors if audience is non-technical |
| **Affiliate program** | Gumroad supports affiliates — music YouTubers promote for commission |

---

## Pricing Philosophy

Octavium is **open-source and free to use**. Revenue comes from:

1. **Convenience** — Signed installer with MIDI library saves time vs building from source
2. **Trust** — EV code-signed by OK Studio Inc. = no SmartScreen, no "unknown publisher"
3. **Support** — Paying customers get priority support and feature input
4. **Goodwill** — Musicians support tools that help them create

The pay-what-you-want model works well for creative tools:
- **$0** = builds from source (power users, developers)
- **$9** = minimum for the installer (casual users who just want it to work)
- **$19** = suggested price (fair value for a useful tool)
- **$49+** = generous supporters who want to see the project thrive

---

## Launch Checklist

### Before Launch
- [ ] Compile and sign the full installer (`build_installer.ps1`)
- [ ] Create Gumroad account and product listing
- [ ] Record a 60-second demo video (screen capture of chord pad workflow)
- [ ] Take 4-5 polished screenshots for product pages
- [ ] Write a launch post for Reddit (r/WeAreTheMusicMakers, r/midi)
- [ ] Set up GitHub Sponsors with tiers
- [ ] Add `FUNDING.yml` to repo

### Launch Day
- [ ] Upload signed installer to Gumroad
- [ ] Create GitHub Release v1.1.1 with unsigned exe + release notes
- [ ] Post to Reddit (r/WeAreTheMusicMakers, r/musicproduction)
- [ ] Post to Hacker News (Show HN)
- [ ] Submit to Product Hunt
- [ ] Share on social media

### Post-Launch (Week 1)
- [ ] Monitor Gumroad analytics and adjust pricing if needed
- [ ] Respond to all GitHub issues and Gumroad messages within 24 hours
- [ ] Post a follow-up with user feedback / testimonials
- [ ] Submit to itch.io

---

## FUNDING.yml Setup

Create `.github/FUNDING.yml` in the repo to enable the GitHub "Sponsor" button:

```yaml
github: owenpkent
ko_fi: okstudio
custom:
  - https://okstudio.gumroad.com/l/octavium
```

This adds a "Sponsor" button to the GitHub repo with links to all funding sources.

---

## Revenue Projections (Conservative)

| Channel | Month 1 | Month 3 | Month 6 |
|---------|---------|---------|---------|
| Gumroad (installer sales) | $50–200 | $200–500 | $500–1,000 |
| GitHub Sponsors | $0–30 | $30–100 | $100–300 |
| Ko-fi / tips | $10–50 | $20–100 | $50–150 |
| itch.io | $0–30 | $30–100 | $50–200 |
| **Total** | **$60–310** | **$280–800** | **$700–1,650** |

These are conservative estimates for a niche music production tool. Growth accelerators:
- A viral Reddit post or YouTube review can 10x a month
- Product Hunt feature can drive 500+ visits in a day
- Word-of-mouth in music production communities compounds over time

---

*Last updated: February 7, 2026*
