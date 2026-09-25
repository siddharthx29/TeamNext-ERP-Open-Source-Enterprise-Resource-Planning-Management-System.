# TeamNext ERP - OTP Login Setup Guide

## ✅ Features Enabled

1. **OTP Login** - Login using One-Time Password sent via email
2. **Multiple Email Support** - Send OTP to multiple email addresses at once
3. **Real Email Delivery** - OTP emails are sent to actual Gmail inboxes
4. **HTML Email Format** - Beautiful, professional email design

## 📧 How to Configure Email (Brevo - Recommended)

### Step 1: Get Brevo SMTP Key

1. Go to: [Brevo SMTP & API Settings](https://app.brevo.com/settings/keys/smtp)
2. Sign in to your Brevo account.
3. Click on **SMTP & API** section.
4. Click on **Generate a new SMTP key**.
5. Give it a name like "TeamNext ERP".
6. **Copy the SMTP Key** (This is your `EMAIL_HOST_PASSWORD`).

### Step 2: Update Your Environment (.env)

Update your `.env` file with these settings:

```env
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-brevo-login-email@example.com
EMAIL_HOST_PASSWORD=your-generated-smtp-key
DEFAULT_FROM_EMAIL=your-verified-sender@example.com
```

### Step 3: Restart Django Server

```bash
# Stop the server (Ctrl+C) and restart
python manage.py runserver
```

## 🚀 How to Use OTP Login

### Single Email:
1. Go to login page
2. Enter your email: `your-email@gmail.com`
3. Click "Send OTP to Email(s)"
4. Check your Gmail inbox
5. Enter the 6-digit OTP code
6. Click "Verify OTP"
7. You'll be logged in to the dashboard

### Multiple Emails:
1. Go to login page
2. Enter multiple emails separated by comma:
   ```
   email1@gmail.com, email2@gmail.com, email3@gmail.com
   ```
3. Click "Send OTP to Email(s)"
4. OTP will be sent to ALL email addresses
5. Use the OTP from any of the emails to login
6. Enter the 6-digit OTP code
7. Click "Verify OTP"

## 📝 Email Format

The OTP email includes:
- **Subject**: "TeamNext ERP - Login OTP"
- **Large OTP Code**: Easy to read 6-digit number
- **Expiration**: 5 minutes validity
- **Security Notice**: Warning about not sharing the code
- **Professional Design**: HTML formatted with TeamNext branding

## 🔒 Security Features

- OTP expires in 5 minutes
- 30-second cooldown between OTP requests (prevents spam)
- OTP is stored in session (not in database)
- Each OTP can only be used once
- HTML and plain text email versions

## 🐛 Troubleshooting

### Emails not arriving?
1. Check `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in settings.py
2. Verify you're using App Password, not regular Gmail password
3. Check spam/junk folder
4. Check Django console for error messages
5. Verify 2-Step Verification is enabled on Google account

### OTP expired?
- Request a new OTP (wait 30 seconds between requests)
- OTPs expire after 5 minutes

### Multiple emails not working?
- Separate emails with comma: `email1@gmail.com, email2@gmail.com`
- Make sure all emails are valid format
- Check console for any error messages

## 📧 Testing Without Email Configuration

If `EMAIL_HOST_USER` or `EMAIL_HOST_PASSWORD` is empty:
- OTP will be displayed in Django console/terminal
- Check the terminal output for the OTP code
- This is useful for testing without configuring email

## 🎯 Example Usage

**Single Email:**
```
Input: user@example.com
Result: OTP sent to user@example.com
```

**Multiple Emails:**
```
Input: user1@example.com, user2@example.com
Result: OTP sent to 2 email addresses
All emails receive the same OTP code
```

## ✅ Success Indicators

- ✅ "OTP sent to your email" message appears
- ✅ Email arrives in Gmail inbox (if configured)
- ✅ OTP code visible in email
- ✅ Can verify OTP and login successfully
