import smtplib

email = "admin@wrsms.online"
password = "Eleonor79!"

try:
    server = smtplib.SMTP_SSL('smtpout.secureserver.net', 465)
    server.login(email, password)
    print("Success! Connection and Auth working.")
except Exception as e:
    print(f"Failed: {e}")