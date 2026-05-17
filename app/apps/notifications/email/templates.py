from __future__ import annotations

from datetime import datetime


def transaction_receipt_template(
    *,
    order_number: str,
    services: list[str],
    total: float,
    payment_status: str,
    timestamp: datetime | None,
) -> str:
    service_items = "".join(f"<li>{service}</li>" for service in services) or "<li>Laundry service</li>"
    paid_at = timestamp.isoformat() if timestamp else "Not available"
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 640px; margin: 0 auto;">
        <h2>Laundry Transaction Receipt</h2>
        <p>Thank you for your payment. Here are your transaction details:</p>
        <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Order Number:</strong> {order_number}</p>
            <p><strong>Total:</strong> KES {total:,.2f}</p>
            <p><strong>Payment Status:</strong> {payment_status}</p>
            <p><strong>Timestamp:</strong> {paid_at}</p>
        </div>
        <h3>Services</h3>
        <ul>{service_items}</ul>
        <p style="color: #6b7280; font-size: 12px;">Campus Laundry O2O System</p>
    </div>
    """


def rate_card_template(services: list[tuple[str, float]]) -> str:
    rows = "".join(
        f"<tr><td style=\"padding: 8px; border-bottom: 1px solid #e5e7eb;\">{name}</td>"
        f"<td style=\"padding: 8px; border-bottom: 1px solid #e5e7eb;\">KES {price:,.2f}</td></tr>"
        for name, price in services
    )
    if not rows:
        rows = "<tr><td colspan=\"2\" style=\"padding: 8px;\">No services are currently available.</td></tr>"

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 640px; margin: 0 auto;">
        <h2>Laundry Service Rate Card</h2>
        <p>Here is the current laundry service rate card.</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr>
                    <th style="text-align: left; padding: 8px;">Service</th>
                    <th style="text-align: left; padding: 8px;">Base Price</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <p style="color: #6b7280; font-size: 12px;">Campus Laundry O2O System</p>
    </div>
    """


def account_notification_template(*, student_name: str, message: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 640px; margin: 0 auto;">
        <h2>Account Notification</h2>
        <p>Hi <strong>{student_name}</strong>,</p>
        <p>{message}</p>
        <p style="color: #6b7280; font-size: 12px;">Campus Laundry O2O System</p>
    </div>
    """
