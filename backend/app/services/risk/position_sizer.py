"""
Position Sizing Engine.
Derives contract quantity strictly from the user's monetary risk budget and stop-loss distance.
Never arbitrarily invests the entire capital allocation into a single trade.
Accounts for exchange contract multiplier, tick size, lot size, and margin requirements.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import math


class ProductSpecification(BaseModel):
    symbol: str = "BTCUSDT"
    contract_value: float = Field(default=0.001, description="Multiplier per contract (e.g. 0.001 BTC per contract)")
    min_order_size: float = Field(default=1.0, description="Minimum order size in contracts")
    lot_size: float = Field(default=1.0, description="Order quantity step / increment")
    tick_size: float = Field(default=0.5, description="Minimum price movement increment")
    settlement_asset: str = "USDT"
    max_exchange_leverage: float = 100.0


class SizingResult(BaseModel):
    is_valid: bool
    rejection_reason: Optional[str] = None
    allocated_capital: float
    risk_percentage: float
    risk_budget_monetary: float
    entry_price: float
    stop_loss: float
    take_profit: float
    stop_distance: float
    target_distance: float
    reward_to_risk: float
    calculated_quantity: float
    notional_exposure: float
    estimated_margin: float
    effective_leverage: float
    estimated_fees: float
    estimated_slippage: float


class PositionSizer:
    @staticmethod
    def round_to_tick(price: float, tick_size: float) -> float:
        """Rounds price to nearest valid tick size."""
        if tick_size <= 0:
            return price
        return round(round(price / tick_size) * tick_size, 6)

    @staticmethod
    def round_to_lot(quantity: float, lot_size: float) -> float:
        """Rounds down quantity to nearest valid lot step."""
        if lot_size <= 0:
            return quantity
        # Use floor to never exceed calculated risk budget
        steps = math.floor(quantity / lot_size)
        return round(steps * lot_size, 6)

    def calculate_position(
        self,
        allocated_capital: float,
        risk_per_trade_pct: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        product: ProductSpecification,
        max_leverage_ceiling: float = 2.0,
        fee_rate_bps: float = 5.0,  # 0.05%
        slippage_bps: float = 2.0   # 0.02%
    ) -> SizingResult:
        """
        Calculates position size:
        1. Monetary risk budget = allocated_capital * (risk_pct / 100)
        2. Stop distance = |entry_price - stop_loss|
        3. Risk per contract = stop_distance * contract_value
        4. Max contracts = risk_budget / risk_per_contract
        5. Leverage and margin constraint enforcement
        """
        if allocated_capital <= 0:
            return self._fail_result("Allocated capital must be greater than zero.", allocated_capital)

        if risk_per_trade_pct <= 0:
            return self._fail_result("Risk percentage must be greater than zero.", allocated_capital)

        stop_distance = abs(entry_price - stop_loss)
        if stop_distance <= 0:
            return self._fail_result("Stop distance cannot be zero.", allocated_capital)

        target_distance = abs(take_profit - entry_price)
        rr = target_distance / stop_distance if stop_distance > 0 else 0.0

        # Core risk budget
        risk_budget = allocated_capital * (risk_per_trade_pct / 100.0)

        # Monetary risk per single contract
        risk_per_contract = stop_distance * product.contract_value
        if risk_per_contract <= 0:
            return self._fail_result("Risk per contract calculation yielded zero.", allocated_capital)

        # Raw quantity from stop distance
        raw_quantity = risk_budget / risk_per_contract

        # Round down to lot size
        quantity = self.round_to_lot(raw_quantity, product.lot_size)

        if quantity < product.min_order_size:
            return self._fail_result(
                f"Calculated size ({quantity} contracts) is below exchange minimum order size ({product.min_order_size}). "
                f"Increase capital allocation or widen stop distance to achieve permitted size.",
                allocated_capital,
                risk_budget=risk_budget,
                entry=entry_price,
                sl=stop_loss,
                tp=take_profit,
                rr=rr
            )

        # Notional exposure: contracts * contract_value * entry_price
        notional_exposure = quantity * product.contract_value * entry_price

        # Max allowed notional based on user's leverage ceiling
        max_notional_permitted = allocated_capital * max_leverage_ceiling
        if notional_exposure > max_notional_permitted:
            # Scale down to meet leverage ceiling
            capped_raw = max_notional_permitted / (product.contract_value * entry_price)
            quantity = self.round_to_lot(capped_raw, product.lot_size)
            if quantity < product.min_order_size:
                return self._fail_result(
                    f"Position capped by max leverage ({max_leverage_ceiling}x) falls below min order size {product.min_order_size}.",
                    allocated_capital,
                    risk_budget=risk_budget
                )
            notional_exposure = quantity * product.contract_value * entry_price

        # Margin requirement (notional / max_leverage_ceiling)
        estimated_margin = notional_exposure / max_leverage_ceiling
        effective_leverage = notional_exposure / allocated_capital if allocated_capital > 0 else 1.0

        # Estimated trading fees & slippage
        fee_rate = fee_rate_bps / 10000.0
        slippage_rate = slippage_bps / 10000.0
        estimated_fees = notional_exposure * fee_rate * 2.0  # round trip
        estimated_slippage = notional_exposure * slippage_rate

        return SizingResult(
            is_valid=True,
            allocated_capital=allocated_capital,
            risk_percentage=risk_per_trade_pct,
            risk_budget_monetary=round(risk_budget, 4),
            entry_price=self.round_to_tick(entry_price, product.tick_size),
            stop_loss=self.round_to_tick(stop_loss, product.tick_size),
            take_profit=self.round_to_tick(take_profit, product.tick_size),
            stop_distance=round(stop_distance, 4),
            target_distance=round(target_distance, 4),
            reward_to_risk=round(rr, 2),
            calculated_quantity=quantity,
            notional_exposure=round(notional_exposure, 2),
            estimated_margin=round(estimated_margin, 2),
            effective_leverage=round(effective_leverage, 2),
            estimated_fees=round(estimated_fees, 4),
            estimated_slippage=round(estimated_slippage, 4)
        )

    def _fail_result(
        self,
        reason: str,
        allocated_capital: float,
        risk_budget: float = 0.0,
        entry: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        rr: float = 0.0
    ) -> SizingResult:
        return SizingResult(
            is_valid=False,
            rejection_reason=reason,
            allocated_capital=allocated_capital,
            risk_percentage=0.0,
            risk_budget_monetary=risk_budget,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            stop_distance=0.0,
            target_distance=0.0,
            reward_to_risk=rr,
            calculated_quantity=0.0,
            notional_exposure=0.0,
            estimated_margin=0.0,
            effective_leverage=0.0,
            estimated_fees=0.0,
            estimated_slippage=0.0
        )
