# Email Setup Instructions for TeamNext ERP

## How to Configure Brevo for OTP Emails (Highly Recommended)

Brevo is more reliable than Gmail and doesn't require constant App Password updates.

### Step 1: Create a Brevo Account
1. Go to: [Brevo](https://www.brevo.com/) and create a free account.
2. Verify your email address.

### Step 2: Get your SMTP Key
1. In the Brevo dashboard, go to the **top-right menu** and select **SMTP & API**.
2. Click on the **SMTP** tab.
3. Click on **Generate a new SMTP key**.
4. Give it a name like "TeamNext ERP Production".
5. **Copy the generated key** immediately — you won't be able to see it again!

### Step 3: Update .env File
Update your `.env` file with these settings:

```env
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-brevo-username@example.com
EMAIL_HOST_PASSWORD=your-generated-brevo-smtp-key
DEFAULT_FROM_EMAIL=your-verified-brevo-sender@example.com
```

### Step 4: Test
1. Go to the login page of TeamNext ERP.
2. Enter your email and click "Login with OTP".
3. Check your inbox (and spam folder) for the OTP.
4. The email will have a professional HTML format with the code clearly displayed.

### Troubleshooting

**If emails don't arrive:**
- Check that EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are set correctly
- Make sure you're using an App Password, not your regular Gmail password
- Check your spam/junk folder
- Verify 2-Step Verification is enabled
- Check the Django console for error messages

**If you see errors:**
- Make sure the App Password is correct (16 characters, no spaces)
- Verify your Gmail address is correct
- Check that less secure app access is not required (App Passwords should work)

### Security Note
- Never commit your App Password to version control
- Keep your settings.py file secure
- App Passwords are safer than using your main Gmail password
