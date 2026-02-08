# Code Signing with an EV Certificate

This guide covers how to sign Octavium's executable and installer using an Extended Validation (EV) code signing certificate on Windows.

---

## Prerequisites

### 1. Hardware Token

EV certificates are stored on a **hardware security module (HSM)** — typically a USB token shipped by your Certificate Authority (CA). Common devices:

- **SafeNet eToken 5110** (most common — used by DigiCert, Sectigo, GlobalSign)
- **YubiKey 5 FIPS**
- **Luna Network HSM** (cloud-based alternative)

Install the token's **middleware/driver** before proceeding:

| Token | Driver |
|-------|--------|
| SafeNet eToken | [SafeNet Authentication Client](https://knowledge.digicert.com/solution/safenet-drivers) |
| YubiKey | [YubiKey Smart Card Minidriver](https://www.yubico.com/support/download/smart-card-drivers-tools/) |

Plug in the token and verify it appears in the driver's management UI.

### 2. Windows SDK (signtool.exe)

`signtool.exe` is included with the **Windows SDK**. If you don't have it:

1. Download the [Windows SDK](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/)
2. During install, select **"Windows SDK Signing Tools for Desktop Apps"** (you can deselect everything else)
3. After install, `signtool.exe` will be at:
   ```
   C:\Program Files (x86)\Windows Kits\10\bin\<version>\x64\signtool.exe
   ```
4. Add that directory to your system `PATH`, or use the full path in commands below.

**Verify installation:**
```powershell
signtool /?
```

### 3. Verify Your Certificate is Visible

With the token plugged in, confirm Windows can see the certificate:

```powershell
# List certificates in the current user's personal store
certutil -user -store My
```

You should see your EV certificate with your company/personal name. Note the **SHA-1 thumbprint** — you'll need it for signing.

You can also check via the SafeNet/YubiKey management UI, or in Windows:
1. Press `Win+R` → `certmgr.msc`
2. Navigate to **Personal → Certificates**
3. Find your EV certificate and double-click to verify it shows the full chain

---

## Signing the Application Executable

### Step 1: Sign Octavium.exe

After building with PyInstaller (`dist\Octavium.exe`), sign it:

```powershell
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /sha1 <YOUR_THUMBPRINT> dist\Octavium.exe
```

**Parameter breakdown:**

| Flag | Purpose |
|------|---------|
| `/tr` | RFC 3161 timestamp server URL (ensures signature remains valid after cert expires) |
| `/td sha256` | Timestamp digest algorithm |
| `/fd sha256` | File digest algorithm |
| `/sha1 <THUMBPRINT>` | Identifies which certificate to use (the SHA-1 thumbprint from `certutil`) |

> **Note:** Your token will prompt for a **PIN** each time you sign. This is expected with EV certificates — the private key never leaves the hardware token.

**Common timestamp servers:**

| CA | Timestamp URL |
|----|---------------|
| DigiCert | `http://timestamp.digicert.com` |
| Sectigo | `http://timestamp.sectigo.com` |
| GlobalSign | `http://timestamp.globalsign.com/?signature=sha2` |

Use the timestamp server that matches your CA.

### Step 2: Verify the Signature

```powershell
signtool verify /pa /v dist\Octavium.exe
```

You should see `Successfully verified: dist\Octavium.exe`.

You can also right-click `Octavium.exe` → **Properties** → **Digital Signatures** tab to visually inspect the signature and certificate chain.

---

## Signing the Installer

After InnoSetup compiles the installer (`OctaviumSetup.exe`), sign it the same way:

```powershell
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /sha1 <YOUR_THUMBPRINT> dist\OctaviumSetup.exe
```

Then verify:

```powershell
signtool verify /pa /v dist\OctaviumSetup.exe
```

---

## Signing Order

The signing order matters. Always sign in this sequence:

1. **Build** `Octavium.exe` with PyInstaller
2. **Sign** `Octavium.exe`
3. **Build** the installer with InnoSetup (it bundles the already-signed `.exe`)
4. **Sign** the installer `OctaviumSetup.exe`

This way, both the application inside the installer and the installer itself carry valid signatures. Windows and SmartScreen will trust both layers.

---

## SmartScreen & EV Certificates

With a standard (OV) code signing certificate, Windows SmartScreen requires building reputation over time — users will see "Windows protected your PC" warnings until enough users have run the software.

**With an EV certificate, SmartScreen reputation is immediate.** Users will not see SmartScreen warnings from the very first download. This is the primary advantage of EV over OV for independent software.

---

## Automated Signing in Build Scripts

To integrate signing into your build pipeline, you can add it to your PowerShell build script. Set your thumbprint as an environment variable to avoid hardcoding it:

```powershell
# Set once per machine (or add to your profile)
$env:OCTAVIUM_SIGN_THUMBPRINT = "<YOUR_THUMBPRINT>"

# Sign command
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /sha1 $env:OCTAVIUM_SIGN_THUMBPRINT dist\Octavium.exe
```

> **Important:** Since EV certificates require a PIN prompt on the hardware token, fully unattended CI/CD signing is not possible in the traditional sense. You must be present to enter the PIN. Some HSM providers offer cloud-based signing solutions (e.g., DigiCert KeyLocker, Azure Trusted Signing) for CI/CD pipelines, but for local builds, the PIN prompt is expected.

---

## Troubleshooting

### "No certificates were found that met all the given criteria"
- Ensure the hardware token is plugged in
- Verify the thumbprint is correct: `certutil -user -store My`
- Check that the token middleware/driver is installed and running

### "The specified timestamp server could not be reached"
- Check your internet connection
- Try an alternative timestamp server from the table above
- Some corporate firewalls block timestamp servers — check with IT

### PIN prompt doesn't appear
- Open the SafeNet/YubiKey management app and verify the token is detected
- Try unplugging and re-inserting the token
- Restart the SafeNet Authentication Client service

### "SignTool Error: An unexpected internal error has occurred"
- Update your Windows SDK to the latest version
- Ensure you're using the 64-bit `signtool.exe` (`x64` directory, not `x86`)

---

*Last updated: February 7, 2026*
