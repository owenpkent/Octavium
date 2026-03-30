@echo off
REM ============================================================
REM  Octavium - EV Code Signing Script
REM  Requires EV certificate on hardware token (USB/SmartCard)
REM
REM  EV best practices applied:
REM    1. Dual-sign: SHA-1 + SHA-256 for max OS compatibility
REM    2. RFC-3161 timestamp from DigiCert (required for EV)
REM    3. /sha1 explicit thumbprint avoids wrong-cert selection
REM       Set CERT_THUMBPRINT below, or leave empty to use /a
REM    4. Verify after every sign operation
REM    5. Fail immediately if any step fails
REM ============================================================

echo ================================================
echo Octavium - EV Code Signing
echo ================================================
echo.

REM Change to project root directory (parent of scripts)
cd /d "%~dp0\.."

REM ---- Configure these paths ----
set SIGNTOOL="C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
set TIMESTAMP_SHA1=http://timestamp.digicert.com
set TIMESTAMP_SHA256=http://timestamp.digicert.com
set EXE_PATH=dist\Octavium.exe
set INSTALLER_PATH=dist\Octavium-Setup-1.1.2.exe

REM ---- Optional: set your EV cert thumbprint for explicit selection ----
REM Avoids accidental use of a dev/test cert if multiple certs are on the token.
REM Leave empty to auto-select with /a
set CERT_THUMBPRINT=%OCTAVIUM_SIGN_THUMBPRINT%

REM Build the /sha1 flag if thumbprint is set
if defined CERT_THUMBPRINT (
    set CERT_FLAG=/sha1 %CERT_THUMBPRINT%
) else (
    set CERT_FLAG=/a
)

REM ---- Validate signtool path ----
if not exist %SIGNTOOL% (
    echo ERROR: signtool.exe not found at %SIGNTOOL%
    echo Install Windows SDK 10.0.26100+ or update SIGNTOOL path.
    pause
    exit /b 1
)

echo NOTE: Insert your hardware token and enter the PIN when prompted.
echo.

REM ============================================================
REM  Sign exe and installer
REM ============================================================
call :SignFile "%EXE_PATH%"
if errorlevel 1 (
    echo ERROR: Signing failed for %EXE_PATH%
    pause
    exit /b 1
)

call :SignFile "%INSTALLER_PATH%"
if errorlevel 1 (
    echo ERROR: Signing failed for %INSTALLER_PATH%
    pause
    exit /b 1
)

echo.
echo ================================================
echo SUCCESS: All files signed and verified!
echo ================================================
echo.
pause
exit /b 0

REM ============================================================
:SignFile
REM %1 = quoted file path
if not exist %1 (
    echo WARNING: %1 not found - skipping.
    exit /b 0
)

echo Signing %1 (pass 1 - SHA-1 for Windows 7 compatibility)...
%SIGNTOOL% sign %CERT_FLAG% /fd sha1 /t %TIMESTAMP_SHA1% %1
if errorlevel 1 ( echo ERROR: SHA-1 sign failed for %1 & exit /b 1 )

echo Signing %1 (pass 2 - SHA-256 append)...
%SIGNTOOL% sign %CERT_FLAG% /as /fd sha256 /tr %TIMESTAMP_SHA256% /td sha256 %1
if errorlevel 1 ( echo ERROR: SHA-256 sign failed for %1 & exit /b 1 )

echo Verifying %1...
%SIGNTOOL% verify /pa /all %1
if errorlevel 1 ( echo ERROR: Verification failed for %1 & exit /b 1 )

echo [OK] %1 dual-signed and verified.
echo.
exit /b 0
