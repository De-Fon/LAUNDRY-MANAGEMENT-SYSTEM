def order_ready_template(student_name: str, order_code: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">Your Laundry is Ready! 🎉</h2>
        <p>Hi <strong>{student_name}</strong>,</p>
        <p>Great news! Your laundry order is ready for pickup.</p>
        <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>Order Code:</strong> {order_code}</p>
        </div>
        <p>Please collect your items at your earliest convenience.</p>
        <p style="color: #6b7280; font-size: 12px;">Campus Laundry O2O System</p>
    </div>
    """

def booking_confirmed_template(student_name: str, pickup_time: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #16a34a;">Booking Confirmed ✅</h2>
        <p>Hi <strong>{student_name}</strong>,</p>
        <p>Your laundry booking has been confirmed.</p>
        <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>Pickup Time:</strong> {pickup_time}</p>
        </div>
        <p>We will collect your laundry at the scheduled time.</p>
        <p style="color: #6b7280; font-size: 12px;">Campus Laundry O2O System</p>
    </div>
    """

def payment_receipt_template(
    student_name: str,
    order_code: str,
    amount: float,
    balance: float,
) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">Payment Receipt 🧾</h2>
        <p>Hi <strong>{student_name}</strong>,</p>
        <p>We have received your payment. Here are the details:</p>
        <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Order Code:</strong> {order_code}</p>
            <p style="margin: 4px 0;"><strong>Amount Paid:</strong> KES {amount:,.2f}</p>
            <p style="margin: 4px 0;"><strong>Outstanding Balance:</strong> KES {balance:,.2f}</p>
        </div>
        <p style="color: #6b7280; font-size: 12px;">Campus Laundry O2O System</p>
    </div>
    """

def account_created_template(student_name: str, email: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">Welcome to Campus Laundry 👋</h2>
        <p>Hi <strong>{student_name}</strong>,</p>
        <p>Your account has been created successfully.</p>
        <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>Email:</strong> {email}</p>
        </div>
        <p>You can now book laundry services, track orders, and manage payments.</p>
        <p style="color: #6b7280; font-size: 12px;">Campus Laundry O2O System</p>
    </div>
    """
