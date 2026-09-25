function Cart({ items, total, onQty, onRemove, onCheckout }) {
  return (
    <aside className="cart">
      <h2>Tu carrito</h2>

      {items.length === 0 && <p>El carrito está vacío.</p>}

      <ul className="cart-list">
        {items.map((item) => (
          <li key={item.id} className="cart-item">
            <img src={item.thumbnail} alt={item.title} width="60" />
            <span className="cart-title">{item.title}</span>
            <span>${item.price.toFixed(2)}</span>
            <div className="qty">
              <button aria-label="Quitar uno" onClick={() => onQty(item.id, -1)}>
                -
              </button>
              <span>{item.quantity}</span>
              <button aria-label="Agregar uno" onClick={() => onQty(item.id, 1)}>
                +
              </button>
            </div>
            <button
              className="remove"
              aria-label={`Eliminar ${item.title}`}
              onClick={() => onRemove(item)}
            >
              x
            </button>
          </li>
        ))}
      </ul>

      <h3>Total: ${total.toFixed(2)}</h3>
      <button className="pay-btn" onClick={onCheckout} disabled={items.length === 0}>
        Pagar
      </button>
    </aside>
  )
}

export default Cart
