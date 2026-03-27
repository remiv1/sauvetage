"""Package des blueprints de l'application Flask."""

from .admin.routes import bp_admin  # type: ignore
from .customer.routes import bp_customer  # type: ignore
from .customer.routes_data import bp_customer_data  # type: ignore
from .dashboard.routes import bp_dashboard  # type: ignore
from .dashboard.routes_data import bp_dashboard_data  # type: ignore
from .inventory.routes import bp_inventory  # type: ignore
from .inventory.routes_data import bp_inventory_data  # type: ignore
from .inventory.routes_htmx import bp_inventory_htmx  # type: ignore
from .order.routes import bp_order  # type: ignore
from .stock.routes import bp_stock  # type: ignore
from .stock.routes_data import bp_stock_data  # type: ignore
from .stock.routes_htmx_council import bp_stock_htmx_council  # type: ignore
from .stock.routes_htmx_orders import bp_stock_htmx_orders  # type: ignore
from .stock.routes_htmx_return import bp_stock_htmx_return  # type: ignore
from .stock.routes_htmx_search import bp_stock_htmx_search  # type: ignore
from .supplier.routes import bp_supplier  # type: ignore
from .supplier.routes_htmx import bp_supplier_htmx  # type: ignore
from .user.routes import bp_user  # type: ignore
