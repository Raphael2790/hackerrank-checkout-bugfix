from decimal import Decimal

from app.models import Payment, PaymentStatus
from app.repository import Repository

CENT = Decimal("0.01")
MAX_INSTALLMENTS = 12
DECLINED_CARD_SUFFIX = "0002"


class PaymentError(Exception):
    pass


class InvalidPayment(PaymentError):
    pass


class PaymentDeclined(PaymentError):
    pass


class RefundNotAllowed(Exception):
    pass


def validate_card(card_number: str) -> None:
    if not isinstance(card_number, str) or len(card_number) != 16 or not card_number.isdigit():
        raise InvalidPayment("Número de cartão deve ter 16 dígitos")


def split_installments(total: Decimal, installments: int) -> list[Decimal]:
    if not isinstance(installments, int) or not 1 <= installments <= MAX_INSTALLMENTS:
        raise InvalidPayment(f"Parcelas devem estar entre 1 e {MAX_INSTALLMENTS}")
    from decimal import ROUND_DOWN
    value = (total / installments).quantize(CENT, rounding=ROUND_DOWN)
    result = [value for _ in range(installments)]
    remainder = total - (value * installments)
    result[0] += remainder
    return result


def charge(
    repo: Repository,
    order_id: int,
    amount: Decimal,
    card_number: str,
    installments: int,
) -> Payment:
    validate_card(card_number)
    plan = split_installments(amount, installments)
    if card_number.endswith(DECLINED_CARD_SUFFIX):
        raise PaymentDeclined("Pagamento recusado pela operadora")

    payment = Payment(
        id=repo.next_payment_id(),
        order_id=order_id,
        amount=amount,
        installments=plan,
        card_last4=card_number[-4:],
    )
    repo.payments[payment.id] = payment
    return payment


def refund(payment: Payment, amount: Decimal | None = None) -> Decimal:
    if payment.status is PaymentStatus.REFUNDED:
        raise RefundNotAllowed("Pagamento já foi totalmente estornado")
    if amount is None:
        amount = payment.refundable_amount
    if amount <= 0:
        raise RefundNotAllowed("Valor do estorno deve ser positivo")
    if amount > payment.refundable_amount:
        raise RefundNotAllowed(
            f"Valor do estorno excede o disponível (R$ {payment.refundable_amount})"
        )

    payment.refunded_amount += amount
    if payment.refundable_amount == 0:
        payment.status = PaymentStatus.REFUNDED
    else:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED
    return amount
