import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowLeft,
  ArrowUpDown,
  BadgeCheck,
  Gift,
  Headphones,
  MessageSquare,
  Minus,
  Package,
  Search,
  ShoppingBag,
  ShoppingCart,
  Trash2,
  X,
  Zap
} from "lucide-react";
import "./style.css";

const API_URL = "";
// FINAL_VISIBLE_CHECKOUT_VERSION=2026-06-02-1

const DELIVERY_METHODS = [
  { id: "pickup", icon: "🏪", title: "Самовывоз", subtitle: "Бесплатно", price: 0 },
  { id: "mcd", icon: "🚆", title: "МЦД-3", subtitle: "100 ₽", price: 100 },
  { id: "moscow", icon: "🚇", title: "По Москве", subtitle: "300 ₽", price: 300 }
];

const PICKUP_POINTS = ["Ипподром", "Раменское", "Фабричная", "Есенинская", "Ильинская", "Кратово", "Отдых"];
const ORDER_TIME_ZONE = "Europe/Moscow";
const WEEKDAYS = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];


function moscowDateParts() {
  const parts = new Intl.DateTimeFormat("ru-RU", {
    timeZone: ORDER_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(new Date());

  return Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, Number(part.value)]));
}


function buildOrderDates(count = 6) {
  const { year, month, day } = moscowDateParts();

  return Array.from({ length: count }, (_, index) => {
    const date = new Date(Date.UTC(year, month - 1, day + index, 12));
    const dateYear = date.getUTCFullYear();
    const dateMonth = String(date.getUTCMonth() + 1).padStart(2, "0");
    const dateDay = String(date.getUTCDate()).padStart(2, "0");

    return {
      value: `${dateYear}-${dateMonth}-${dateDay}`,
      label: `${dateDay}.${dateMonth}`,
      weekday: WEEKDAYS[date.getUTCDay()],
      sameDay: index === 0
    };
  });
}


function deliveryMethodTitle(id) {
  return DELIVERY_METHODS.find((item) => item.id === id)?.title || "Не указан";
}


function tg() {
  return window.Telegram?.WebApp;
}

function tgHaptic(type = "light") {
  try {
    tg()?.HapticFeedback?.impactOccurred?.(type);
  } catch {
    // ignore haptic errors
  }
}

function getInitData() {
  return tg()?.initData || "";
}

function normalizeReferralStart(value) {
  if (!value) return "";
  return String(value).trim();
}

function getReferralStartParam() {
  const app = tg();
  const unsafeValue = normalizeReferralStart(app?.initDataUnsafe?.start_param);

  const hashParams = new URLSearchParams(String(window.location.hash || "").replace(/^#/, ""));
  const queryParams = new URLSearchParams(window.location.search || "");

  const urlValue = normalizeReferralStart(
    hashParams.get("tgWebAppStartParam")
      || hashParams.get("start_param")
      || hashParams.get("startapp")
      || queryParams.get("tgWebAppStartParam")
      || queryParams.get("start_param")
      || queryParams.get("startapp")
  );

  const value = unsafeValue || urlValue;

  if (value) {
    localStorage.setItem("syndicate_ref_start_param", value);
    return value;
  }

  return localStorage.getItem("syndicate_ref_start_param") || "";
}

function getTelegramUser() {
  const app = tg();
  app?.ready();
  app?.expand();
  app?.setHeaderColor?.("#02021A");
  app?.setBackgroundColor?.("#02021A");

  const user = app?.initDataUnsafe?.user;

  return {
    id: user?.id || 777001,
    username: user?.username || "test_user"
  };
}

function normalizeText(value) {
  return String(value || "").toLowerCase().trim();
}

function isVisibleCategory(category) {
  const name = normalizeText(category?.name);
  return name !== "без категории" && name !== "bez kategorii" && name !== "uncategorized";
}

function statusRu(status) {
  return {
    new: "Ожидает",
    confirmed: "Подтверждён",
    cancelled: "Отменён"
  }[status] || status;
}

function bonusTxTitle(type) {
  return {
    cashback: "Кэшбэк",
    spend: "Списание",
    referral: "Реферал"
  }[type] || type;
}

function cartItemForProduct(cart, product) {
  const items = cart?.items || [];
  return items.find((item) => item.product_id === product.id);
}


function ProductImage({ item }) {
  if (item.image_url) {
    return <img src={item.image_url} alt={item.name} />;
  }

  return (
    <div className="productFallback">
      <span>S</span>
    </div>
  );
}

function CategoryIcon({ item }) {
  if (item.image_url) {
    return <img src={item.image_url} alt={item.name} />;
  }

  return <span>{item.emoji || "S"}</span>;
}

function ProductModal({ product, onClose, onAdd }) {
  const variants = product?.variants || [];
  const [selectedVariant, setSelectedVariant] = useState(variants.length ? "" : null);
  const [quantity, setQuantity] = useState(1);

  useEffect(() => {
    setSelectedVariant((product?.variants || []).length ? "" : null);
    setQuantity(1);
  }, [product?.id]);

  useEffect(() => {
    if (!product) return undefined;

    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
    };
  }, [product]);

  if (!product) return null;

  const variantRequired = variants.length > 0;
  const canAdd = !variantRequired || Boolean(selectedVariant);

  return (
    <div className="productDetailOverlay" onClick={onClose}>
      <section className="productDetailPage" onClick={(e) => e.stopPropagation()}>
        <div className="productDetailTopbar">
          <button className="productDetailBack" type="button" onClick={onClose}>
            <ArrowLeft size={20} />
            Назад
          </button>
        </div>

        <div className="productDetailScroll">
          <div className="productDetailImageWrap">
            <div className="productDetailImageCard">
              <div className="productDetailImageGlow productDetailImageGlowLeft" />
              <div className="productDetailImageGlow productDetailImageGlowRight" />
              <ProductImage item={product} />
            </div>
          </div>

          <div className="productDetailBody">
            <h2>{product.name}</h2>
            <div className="productDetailPrice">{product.price} ₽</div>

            <div className="productDetailSection">
              <div className="productDetailLabel">Описание</div>
              <p>{product.description || "-"}</p>
            </div>

            {variantRequired && (
              <div className="productDetailSection">
                <h3>Выберите вариант <em>*</em></h3>
                <div className="productDetailVariants">
                  {variants.map((variant) => (
                    <button
                      type="button"
                      key={variant}
                      className={`productDetailChip ${selectedVariant === variant ? "active" : ""}`}
                      onClick={() => setSelectedVariant(variant)}
                    >
                      {variant}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="productDetailFooter">
          <div className="productDetailQty" aria-label="Количество товара">
            <button type="button" onClick={() => setQuantity((q) => Math.max(1, q - 1))}>−</button>
            <span>{quantity}</span>
            <button type="button" onClick={() => setQuantity((q) => q + 1)}>+</button>
          </div>

          <button
            className="productDetailAddButton"
            type="button"
            disabled={!canAdd}
            onClick={() => onAdd(product.id, selectedVariant || null, quantity)}
          >
            <ShoppingCart size={22} />
            {canAdd ? "Добавить в корзину" : "Выберите вариант"}
          </button>
        </div>
      </section>
    </div>
  );
}

function App() {
  const user = useMemo(() => getTelegramUser(), []);
  const [screen, setScreen] = useState("categories");
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState({ items: [], total: 0, count: 0 });
  const [bonus, setBonus] = useState({ balance: 0, referral_code: "", referral_link: "", transactions: [] });
  const [bonusToUse, setBonusToUse] = useState(0);
  const [promoCodeInput, setPromoCodeInput] = useState("");
  const [appliedPromo, setAppliedPromo] = useState(null);
  const [orders, setOrders] = useState([]);
  const [activeCategory, setActiveCategory] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [categorySearch, setCategorySearch] = useState("");
  const [productSearch, setProductSearch] = useState("");
  const [priceSort, setPriceSort] = useState("default");
  const [phone, setPhone] = useState("");
  const [comment, setComment] = useState("");
  const [deliveryMethod, setDeliveryMethod] = useState("pickup");
  const [pickupPoint, setPickupPoint] = useState("Ипподром");
  const [mcdStation, setMcdStation] = useState("");
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [dateAnchor, setDateAnchor] = useState(() => buildOrderDates(1)[0].value);
  const [deliveryDate, setDeliveryDate] = useState(() => buildOrderDates(1)[0].value);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [orderSubmitting, setOrderSubmitting] = useState(false);

  const filteredCategories = useMemo(() => {
    const q = normalizeText(categorySearch);
    const visible = categories.filter(isVisibleCategory);
    if (!q) return visible;
    return visible.filter((c) => normalizeText(`${c.name} ${c.emoji || ""}`).includes(q));
  }, [categories, categorySearch]);

  const filteredProducts = useMemo(() => {
    const q = normalizeText(productSearch);

    let result = products.filter((p) => {
      if (!q) return true;
      return normalizeText(`${p.name} ${p.description || ""} ${(p.variants || []).join(" ")} ${p.price}`).includes(q);
    });

    if (priceSort === "cheap") {
      result = [...result].sort((a, b) => Number(a.price) - Number(b.price));
    }

    if (priceSort === "expensive") {
      result = [...result].sort((a, b) => Number(b.price) - Number(a.price));
    }

    return result;
  }, [products, productSearch, priceSort]);


  const deliveryFee = useMemo(() => {
    return DELIVERY_METHODS.find((item) => item.id === deliveryMethod)?.price || 0;
  }, [deliveryMethod]);

  const orderDates = useMemo(() => buildOrderDates(7), [dateAnchor]);
  const dateSurcharge = deliveryDate === orderDates[0]?.value ? 100 : 0;

  const promoBaseTotal = useMemo(() => {
    return Number(cart.total || 0) + Number(deliveryFee || 0) + Number(dateSurcharge || 0);
  }, [cart.total, deliveryFee, dateSurcharge]);

  const promoDiscount = useMemo(() => {
    if (!appliedPromo?.percent) return 0;
    return Math.floor(Number(promoBaseTotal || 0) * Number(appliedPromo.percent || 0) / 100);
  }, [appliedPromo, promoBaseTotal]);

  const orderTotal = useMemo(() => {
    return Math.max(Number(promoBaseTotal || 0) - Number(promoDiscount || 0), 0);
  }, [promoBaseTotal, promoDiscount]);

  const maxBonusToUse = useMemo(() => {
    return Math.min(Number(bonus.balance || 0), Math.floor(Number(orderTotal || 0) * 0.4));
  }, [bonus.balance, orderTotal]);

  const appliedBonus = Math.min(Number(bonusToUse || 0), Number(maxBonusToUse || 0));

  const finalOrderTotal = useMemo(() => {
    return Math.max(Number(orderTotal || 0) - Number(appliedBonus || 0), 0);
  }, [orderTotal, appliedBonus]);

  const cartHasStockProblems = useMemo(() => {
    return (cart.items || []).some((item) => item.stock_status && item.stock_status !== "ok");
  }, [cart.items]);

  useEffect(() => {
    const refreshDates = () => {
      setDateAnchor(buildOrderDates(1)[0].value);
    };

    const handleVisibilityChange = () => {
      if (!document.hidden) refreshDates();
    };

    const timer = window.setInterval(refreshDates, 1000);
    window.addEventListener("focus", refreshDates);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refreshDates);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  useEffect(() => {
    if (!orderDates.some((item) => item.value === deliveryDate)) {
      setDeliveryDate(orderDates[0]?.value || "");
    }
  }, [orderDates, deliveryDate]);

  async function api(path, options = {}) {
    const res = await fetch(`${API_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": getInitData(),
        "X-Referral-Start-Param": getReferralStartParam()
      },
      ...options
    });

    if (!res.ok) {
      const data = await res.json().catch(async () => {
        const text = await res.text().catch(() => "");
        return { detail: text };
      });
      throw new Error(data.detail || `Ошибка запроса ${res.status}`);
    }

    return res.json();
  }

  function toast(text, type = "success") {
    setNotice(text);
    setTimeout(() => setNotice(""), 1800);
    tg()?.HapticFeedback?.notificationOccurred?.(type);
  }

  async function run(fn) {
    try {
      setLoading(true);
      await fn();
    } catch (e) {
      toast(e.message || "Ошибка", "error");
    } finally {
      setLoading(false);
    }
  }

  async function registerAppUser() {
    await api("/api/register", { method: "POST" });
  }

  async function loadCategories() {
    setCategories(await api("/api/categories"));
  }

  async function loadCart() {
    setCart(await api("/api/cart"));
  }

  async function loadBonus() {
    setBonus(await api("/api/bonus"));
  }

  function getPageScrollTop() {
    return window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0;
  }

  function restorePageScrollTop(value) {
    const top = Math.max(Number(value || 0), 0);

    const restore = () => {
      window.scrollTo(0, top);
      document.documentElement.scrollTop = top;
      document.body.scrollTop = top;
    };

    restore();
    requestAnimationFrame(() => {
      restore();
      requestAnimationFrame(restore);
    });
  }

  async function openCategory(category) {
    const keepScroll = screen === "products";
    const scrollTop = keepScroll ? getPageScrollTop() : 0;

    await run(async () => {
      setActiveCategory(category);
      setProductSearch("");
      setPriceSort("default");
      setProducts(await api(`/api/products?category_id=${category.id}`));

      if (!keepScroll) {
        setScreen("products");
      }
    });

    if (keepScroll) {
      restorePageScrollTop(scrollTop);
    }
  }

  async function openCart() {
    await run(async () => {
      await loadCart();
      await loadBonus();
      setBonusToUse(0);
      setScreen("cart");
    });
  }

  async function addToCart(productId, variant = null, quantity = 1) {
    await run(async () => {
      await api("/api/cart/add", {
        method: "POST",
        body: JSON.stringify({ product_id: productId, quantity, variant })
      });
      await loadCart();
      toast("Товар добавлен");
    });
  }

  async function updateCart(productId, quantity, variant = null) {
    await run(async () => {
      await api(quantity <= 0 ? "/api/cart/remove" : "/api/cart/update", {
        method: "POST",
        body: JSON.stringify({ product_id: productId, quantity, variant })
      });
      await loadCart();
    });
  }

  async function removeCartItem(productId, variant = null) {
    await run(async () => {
      await api("/api/cart/remove", {
        method: "POST",
        body: JSON.stringify({ product_id: productId, variant })
      });
      await loadCart();
      toast("Товар удалён из корзины");
    });
  }

  async function clearCart() {
    await run(async () => {
      await api("/api/cart/clear", { method: "POST" });
      await loadCart();
      setAppliedPromo(null);
      setPromoCodeInput("");
      setBonusToUse(0);
      toast("Корзина очищена");
    });
  }

  async function applyPromocode() {
    const code = promoCodeInput.trim();

    if (!code) {
      toast("Введите промокод", "error");
      return;
    }

    await run(async () => {
      const promo = await api("/api/promocode/check", {
        method: "POST",
        body: JSON.stringify({
          code,
          delivery_method: deliveryMethod,
          delivery_date: deliveryDate
        })
      });

      setAppliedPromo({
        code: promo.code,
        percent: promo.percent
      });
      setPromoCodeInput(promo.code);
      setBonusToUse(0);
      toast(`Промокод ${promo.code} применён`);
    });
  }

  function removePromocode() {
    setAppliedPromo(null);
    setPromoCodeInput("");
    setBonusToUse(0);
    toast("Промокод убран");
  }

  async function createOrder() {
    if (orderSubmitting) return;

    setOrderSubmitting(true);
    setNotice("Оформляем заказ...");

    try {
      if (cartHasStockProblems) {
        throw new Error("В корзине есть товары, которых уже нет в наличии. Удалите их или уменьшите количество.");
      }

      if (phone.trim().length < 10) {
        throw new Error("Введите корректный телефон");
      }

      if (deliveryMethod === "pickup" && !pickupPoint) {
        throw new Error("Выберите пункт самовывоза");
      }

      if (deliveryMethod === "mcd" && mcdStation.trim().length < 2) {
        throw new Error("Введите станцию МЦД-3");
      }

      if (deliveryMethod === "moscow" && deliveryAddress.trim().length < 2) {
        throw new Error("Введите ближайшую станцию метро");
      }

      if (!orderDates.some((item) => item.value === deliveryDate)) {
        throw new Error("Выберите дату получения");
      }

      const data = await api("/api/orders", {
        method: "POST",
        body: JSON.stringify({
          phone,
          comment,
          delivery_method: deliveryMethod,
          delivery_price: deliveryFee,
          bonus_to_use: appliedBonus,
          promo_code: appliedPromo?.code || null,
          pickup_point: deliveryMethod === "pickup" ? pickupPoint : null,
          mcd_station: deliveryMethod === "mcd" ? mcdStation : null,
          delivery_address: deliveryMethod === "moscow" ? deliveryAddress : null,
          delivery_date: deliveryDate
        })
      });

      setPhone("");
      setComment("");
      setDeliveryAddress("");
      setDeliveryMethod("pickup");
      setPickupPoint("Ипподром");
      setMcdStation("");
      setDeliveryAddress("");
      setDeliveryDate(buildOrderDates(1)[0].value);
      setBonusToUse(0);
      setAppliedPromo(null);
      setPromoCodeInput("");

      // Backend уже очистил корзину и поставил уведомления в очередь.
      // Не ждём повторные запросы loadCart/loadBonus, чтобы оформление ощущалось мгновенным.
      setCart({ items: [], total: 0, count: 0 });
      setBonus((current) => ({
        ...current,
        balance: Math.max(Number(current.balance || 0) - Number(appliedBonus || 0), 0)
      }));
      setScreen("categories");
      toast(`Заказ №${data.order_id} создан`);
    } catch (e) {
      toast(e.message || "Ошибка оформления заказа", "error");
    } finally {
      setOrderSubmitting(false);
    }
  }

  async function openOrders() {
    await run(async () => {
      setOrders(await api("/api/orders/my"));
      setScreen("orders");
    });
  }

  async function openBonus() {
    await run(async () => {
      await loadBonus();
      setScreen("bonus");
    });
  }

  async function copyReferralLink() {
    const text = bonus.referral_link || bonus.referral_code;
    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      toast("Реферальная ссылка скопирована");
    } catch {
      toast("Ссылка: " + text);
    }
  }

  function togglePriceSort() {
    setPriceSort((current) => {
      if (current === "default") return "cheap";
      if (current === "cheap") return "expensive";
      return "default";
    });
  }

  function priceSortLabel() {
    if (priceSort === "cheap") return "Сначала дешевле";
    if (priceSort === "expensive") return "Сначала дороже";
    return "Сортировать по цене";
  }

  useEffect(() => {
    run(async () => {
      await registerAppUser();
      await loadCategories();
      await loadCart();
      await loadBonus();
    });
  }, []);


  useEffect(() => {
    // MULTIPLATFORM_TELEGRAM_VIEWPORT_MANAGER
    const root = document.documentElement;

    const numberFrom = (...values) => {
      for (const value of values) {
        const numeric = Number(value);
        if (Number.isFinite(numeric) && numeric > 0) return numeric;
      }

      return 0;
    };

    const applyTelegramSafeArea = () => {
      try {
        const app = tg();
        const platform = String(app?.platform || "web").toLowerCase();
        const isFullscreen = Boolean(app?.isFullscreen);

        const safeTop = numberFrom(app?.safeAreaInset?.top, app?.contentSafeAreaInset?.top);
        const safeBottom = numberFrom(app?.safeAreaInset?.bottom, app?.contentSafeAreaInset?.bottom);
        const viewportHeight = numberFrom(
          app?.viewportStableHeight,
          app?.viewportHeight,
          window.visualViewport?.height,
          window.innerHeight,
          document.documentElement.clientHeight
        );

        const isIOS = platform.includes("ios") || platform.includes("iphone") || platform.includes("ipad");
        const isAndroid = platform.includes("android");

        // В fullscreen Telegram системные кнопки могут быть поверх Mini App,
        // даже если safeAreaInset.top возвращает 0.
        const fullscreenFallbackTop = isFullscreen ? (isIOS ? 82 : 62) : 0;
        const top = Math.max(safeTop, fullscreenFallbackTop, 0);
        const bottom = Math.max(safeBottom, 0);
        const height = Math.max(viewportHeight || 0, 560);

        root.style.setProperty("--tg-safe-top", `${top}px`);
        root.style.setProperty("--tg-safe-bottom-px", `${bottom}px`);
        root.style.setProperty("--app-height", `${height}px`);
        root.style.setProperty("--viewport-height", `${height}px`);

        document.body.dataset.tgPlatform = platform;
        document.body.dataset.tgFullscreen = isFullscreen ? "1" : "0";
        document.body.classList.toggle("is-ios", isIOS);
        document.body.classList.toggle("is-android", isAndroid);
        document.body.classList.toggle("is-tg-fullscreen", isFullscreen);
      } catch {
        root.style.setProperty("--tg-safe-top", "0px");
        root.style.setProperty("--tg-safe-bottom-px", "0px");
        root.style.setProperty("--app-height", `${Math.max(window.innerHeight || 0, 560)}px`);
      }
    };

    try {
      const app = tg();
      app?.ready?.();
      app?.expand?.();
      app?.setHeaderColor?.("#050210");
      app?.setBackgroundColor?.("#050210");
      app?.disableVerticalSwipes?.();

      applyTelegramSafeArea();
      app?.onEvent?.("safeAreaChanged", applyTelegramSafeArea);
      app?.onEvent?.("contentSafeAreaChanged", applyTelegramSafeArea);
      app?.onEvent?.("viewportChanged", applyTelegramSafeArea);
    } catch {
      applyTelegramSafeArea();
    }

    const handleFastTap = (event) => {
      const target = event.target?.closest?.("button, a, .categoryCard, .productCard, .cleanProductCard, .deliveryOption, .dateOption, .choicePill, .variantChip");
      if (!target || target.disabled || target.getAttribute("aria-disabled") === "true") return;
      tgHaptic("light");
    };

    window.addEventListener("resize", applyTelegramSafeArea, { passive: true });
    window.addEventListener("orientationchange", applyTelegramSafeArea, { passive: true });
    window.visualViewport?.addEventListener?.("resize", applyTelegramSafeArea, { passive: true });
    document.addEventListener("pointerdown", handleFastTap, { passive: true });

    requestAnimationFrame(applyTelegramSafeArea);
    setTimeout(applyTelegramSafeArea, 300);
    setTimeout(applyTelegramSafeArea, 900);

    return () => {
      document.removeEventListener("pointerdown", handleFastTap);
      window.removeEventListener("resize", applyTelegramSafeArea);
      window.removeEventListener("orientationchange", applyTelegramSafeArea);
      window.visualViewport?.removeEventListener?.("resize", applyTelegramSafeArea);

      try {
        const app = tg();
        app?.offEvent?.("safeAreaChanged", applyTelegramSafeArea);
        app?.offEvent?.("contentSafeAreaChanged", applyTelegramSafeArea);
        app?.offEvent?.("viewportChanged", applyTelegramSafeArea);
      } catch {
        // ignore cleanup errors
      }
    };
  }, []);

  const visibleCategories = filteredCategories;

  return (
    <main className="app">
      <div className="ambient ambientOne"></div>
      <div className="ambient ambientTwo"></div>

      <header className="hero">
        <div className="heroTop">
          <div className="heroSpacer" aria-hidden="true"></div>

          <div className="brand">
            <img src="/syndicate-header.jpeg" alt="SYNDICATE" />
            <h1>SYNDICATE</h1>
            <p>VAPE SHOP</p>
          </div>

          <button className="glassIcon cartIcon" type="button" onClick={openCart} disabled={loading}>
            <ShoppingCart size={24} />
            {cart.count > 0 && <span>{cart.count}</span>}
          </button>
        </div>
      </header>

      {notice && <div className="notice">{notice}</div>}

      {screen === "categories" && (
        <div className="searchBox">
          <Search size={22} />
          <input
            placeholder="Поиск категорий..."
            value={categorySearch}
            onChange={(e) => setCategorySearch(e.target.value)}
          />
          {categorySearch && (
            <button type="button" onClick={() => setCategorySearch("")}>
              <X size={18} />
            </button>
          )}
        </div>
      )}

      {screen === "products" && (
        <>
          <button type="button" className="backBtn" onClick={() => setScreen("categories")}>
            <ArrowLeft size={16} />
            К категориям
          </button>

          <div className="searchBox">
            <Search size={22} />
            <input
              placeholder="Поиск товаров..."
              value={productSearch}
              onChange={(e) => setProductSearch(e.target.value)}
            />
            {productSearch && (
              <button type="button" onClick={() => setProductSearch("")}>
                <X size={18} />
              </button>
            )}
          </div>
        </>
      )}

      {screen === "products" && activeCategory && (
        <nav className="categoryTabs" aria-label="Категории товаров">
          {categories.filter(isVisibleCategory).map((c) => {
            const active = c.id === activeCategory.id;

            return (
              <button
                type="button"
                key={c.id}
                className={active ? "active" : ""}
                onClick={() => {
                  if (!active) openCategory(c);
                }}
                disabled={loading}
              >
                <CategoryIcon item={c} />
                {c.name}
              </button>
            );
          })}
        </nav>
      )}

      {screen === "products" && (
        <button
          type="button"
          className={`sortPill ${priceSort !== "default" ? "active" : ""}`}
          onClick={togglePriceSort}
        >
          <ArrowUpDown size={21} />
          <span>{priceSortLabel()}</span>
        </button>
      )}

      {screen === "categories" && (
        <section className="section">
          <div className="sectionHead">
            <h2>Категории</h2>
            <span>{filteredCategories.length}</span>
          </div>

          {categories.length === 0 && <p className="muted">Категорий пока нет</p>}
          {categories.length > 0 && filteredCategories.length === 0 && <p className="muted">Ничего не найдено</p>}

          <div className="categoryGrid">
            {filteredCategories.map((c) => (
              <button className="categoryCard" type="button" key={c.id} onClick={() => openCategory(c)} disabled={loading}>
                <div className="categoryPreview">
                  <CategoryIcon item={c} />
                </div>
                <b>{c.emoji ? `${c.emoji} ` : ""}{c.name}</b>
                <small>Открыть</small>
              </button>
            ))}
          </div>
        </section>
      )}

      {screen === "products" && (
        <section className="section">
          <div className="sectionHead">
            <h2>{activeCategory?.name}</h2>
            <span>{filteredProducts.length}</span>
          </div>

          {products.length === 0 && <p className="muted">Товаров пока нет</p>}
          {products.length > 0 && filteredProducts.length === 0 && <p className="muted">Ничего не найдено</p>}

          <div className="productGrid">
            {filteredProducts.map((p) => {
              const cartEntry = cartItemForProduct(cart, p);
              const hasVariants = p.variants?.length > 0;

              return (
                <article className="productCard cleanProductCard" key={p.id} onClick={() => setSelectedProduct(p)}>
                  <div className="productPhoto">
                    <ProductImage item={p} />
                  </div>

                  <div className="productInfo">
                    <h3>{p.name}</h3>
                    {p.variants?.length > 0 && <small className="productVariantsHint">Есть варианты</small>}
                    <b>{p.price} ₽</b>
                  </div>

                  {cartEntry && !hasVariants ? (
                    <div className="cardQtyControl" onClick={(e) => e.stopPropagation()}>
                      <button type="button" onClick={() => updateCart(p.id, cartEntry.quantity - 1, null)} disabled={loading}>−</button>
                      <span>{cartEntry.quantity}</span>
                      <button type="button" onClick={() => updateCart(p.id, cartEntry.quantity + 1, null)} disabled={loading}>+</button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="cardAddButton"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (hasVariants) {
                          setSelectedProduct(p);
                          return;
                        }
                        addToCart(p.id);
                      }}
                      disabled={loading}
                    >
                      <ShoppingCart size={22} />
                      <span>Добавить</span>
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      )}

      {screen === "cart" && (
        <section className="section">
          <div className="sectionHead">
            <h2>Корзина</h2>
            <span>{cart.count || 0}</span>
          </div>

          {cart.items.length === 0 ? (
            <p className="muted">Корзина пустая</p>
          ) : (
            <>
              <div className="cartList">
                {cart.items.map((i) => {
                  const hasStockProblem = i.stock_status && i.stock_status !== "ok";
                  const outOfStock = i.stock_status === "out";
                  const availableStock = Number(i.available_stock || 0);
                  const canIncrease = !hasStockProblem && Number(i.quantity || 0) < availableStock;

                  return (
                    <div
                      className={`cartItem ${hasStockProblem ? "cartItemProblem" : ""} ${outOfStock ? "cartItemOut" : ""}`}
                      key={`${i.product_id}:${i.variant || "default"}`}
                    >
                      <div className="cartImage">
                        <ProductImage item={i} />
                      </div>

                      <div className="cartItemInfo">
                        <b>{i.name}</b>
                        {i.variant && <div className="cartVariant">Вариант: {i.variant}</div>}
                        <small>{i.price} ₽ / шт.</small>

                        {hasStockProblem && (
                          <div className="cartStockAlert">
                            {i.stock_message || "Товар закончился. Удалите его из корзины."}
                          </div>
                        )}

                        {!hasStockProblem && availableStock > 0 && availableStock <= 3 && (
                          <div className="cartStockHint">Осталось: {availableStock} шт.</div>
                        )}

                        <div className="qtyControl">
                          <button
                            type="button"
                            onClick={() => updateCart(i.product_id, i.quantity - 1, i.variant || null)}
                            disabled={outOfStock}
                          >
                            <Minus size={16} />
                          </button>
                          <span>{i.quantity}</span>
                          <button
                            type="button"
                            onClick={() => updateCart(i.product_id, i.quantity + 1, i.variant || null)}
                            disabled={!canIncrease}
                          >
                            +
                          </button>
                        </div>

                        {hasStockProblem && (
                          <button
                            type="button"
                            className="cartRemoveInline"
                            onClick={() => removeCartItem(i.product_id, i.variant || null)}
                          >
                            <Trash2 size={16} />
                            Удалить из корзины
                          </button>
                        )}
                      </div>

                      <strong>{i.price * i.quantity} ₽</strong>
                    </div>
                  );
                })}
              </div>

              {cartHasStockProblems && (
                <div className="cartProblemNotice">
                  В корзине есть товары, которых уже нет в наличии или их осталось меньше, чем выбрано.
                  Удалите товар или уменьшите количество.
                </div>
              )}

              <div className="checkout orderCheckout">
                <div className="checkoutBlock">
                  <h3>Способ получения <em>*</em></h3>
                  <div className="deliveryOptions">
                    {DELIVERY_METHODS.map((method) => (
                      <button
                        type="button"
                        key={method.id}
                        className={`deliveryOption ${deliveryMethod === method.id ? "active" : ""}`}
                        onClick={() => setDeliveryMethod(method.id)}
                      >
                        <span className="deliveryIcon">{method.icon}</span>
                        <span>
                          <b>{method.title}</b>
                          <small>{method.subtitle}</small>
                        </span>
                        <i>{deliveryMethod === method.id ? "✓" : ""}</i>
                      </button>
                    ))}
                  </div>
                </div>

                {deliveryMethod === "pickup" && (
                  <div className="checkoutBlock">
                    <h3>Пункт самовывоза <em>*</em></h3>
                    <div className="optionGrid">
                      {PICKUP_POINTS.map((point) => (
                        <button
                          type="button"
                          key={point}
                          className={`choicePill ${pickupPoint === point ? "active" : ""}`}
                          onClick={() => setPickupPoint(point)}
                        >
                          📍 {point}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {deliveryMethod === "mcd" && (
                  <div className="checkoutBlock">
                    <h3>Станция МЦД-3 <em>*</em></h3>
                    <input
                      placeholder="Например, Электрозаводская"
                      value={mcdStation}
                      onChange={(e) => setMcdStation(e.target.value)}
                    />
                  </div>
                )}

                {deliveryMethod === "moscow" && (
                  <div className="checkoutBlock">
                    <h3>Ближайшая станция метро <em>*</em></h3>
                    <input
                      placeholder="Например, Тверская"
                      value={deliveryAddress}
                      onChange={(e) => setDeliveryAddress(e.target.value)}
                    />
                  </div>
                )}

                <div className="checkoutBlock dateCheckoutBlock">
                  <h3>Дата <em>*</em></h3>
                  <div className="dateOptions">
                    {orderDates.map((date) => (
                      <button
                        type="button"
                        key={date.value}
                        className={`dateOption ${deliveryDate === date.value ? "active" : ""}`}
                        onClick={() => setDeliveryDate(date.value)}
                      >
                        <b>{date.label}</b>
                        <span>{date.weekday}</span>
                        {date.sameDay && <small>+100 ₽</small>}
                      </button>
                    ))}
                  </div>
                  <p className="sameDayHint">День-в-день: +100 ₽</p>
                </div>

                <div className="checkoutBlock">
                  <h3>Контакты <em>*</em></h3>
                  <input placeholder="Телефон" value={phone} onChange={(e) => setPhone(e.target.value)} />
                  <textarea placeholder="Комментарий: время, способ связи, пожелания" value={comment} onChange={(e) => setComment(e.target.value)} />
                </div>

                <div className="promocodeCard">
                  <div>
                    <strong>Промокод</strong>
                    <span>Скидка применяется к товарам и доставке</span>
                  </div>

                  <div className="promocodeForm">
                    <input
                      placeholder="Введите промокод"
                      value={promoCodeInput}
                      onChange={(e) => setPromoCodeInput(e.target.value.toUpperCase())}
                      disabled={Boolean(appliedPromo)}
                    />

                    {appliedPromo ? (
                      <button type="button" onClick={removePromocode}>
                        Убрать
                      </button>
                    ) : (
                      <button type="button" onClick={applyPromocode} disabled={!promoCodeInput.trim()}>
                        Применить
                      </button>
                    )}
                  </div>

                  {appliedPromo && (
                    <small className="promoApplied">
                      {appliedPromo.code}: −{promoDiscount} ₽ ({appliedPromo.percent}%)
                    </small>
                  )}
                </div>

                <div className="bonusRedeemCard">
                  <div>
                    <strong>SYNDICATE BONUS</strong>
                    <span>Доступно: {bonus.balance || 0} баллов</span>
                    <small>Можно списать до 40% заказа: {maxBonusToUse} ₽</small>
                  </div>

                  {appliedBonus > 0 ? (
                    <button type="button" onClick={() => setBonusToUse(0)}>
                      Убрать списание
                    </button>
                  ) : (
                    <button
                      type="button"
                      disabled={maxBonusToUse <= 0}
                      onClick={() => setBonusToUse(maxBonusToUse)}
                    >
                      Списать баллы
                    </button>
                  )}
                </div>

                <div className="total">
                  <span>Товары</span>
                  <b>{cart.total} ₽</b>
                </div>
                <div className="total">
                  <span>{deliveryMethodTitle(deliveryMethod)}</span>
                  <b>{deliveryFee} ₽</b>
                </div>
                {dateSurcharge > 0 && (
                  <div className="total dateSurchargeTotal">
                    <span>День-в-день</span>
                    <b>+{dateSurcharge} ₽</b>
                  </div>
                )}
                {promoDiscount > 0 && (
                  <div className="total promoTotal">
                    <span>Промокод {appliedPromo?.code}</span>
                    <b>−{promoDiscount} ₽</b>
                  </div>
                )}
                {appliedBonus > 0 && (
                  <div className="total bonusTotal">
                    <span>Списано бонусов</span>
                    <b>−{appliedBonus} ₽</b>
                  </div>
                )}
                <div className="total finalTotal">
                  <span>Итого</span>
                  <b>{finalOrderTotal} ₽</b>
                </div>

                <button type="button" className="primary" onClick={createOrder} disabled={orderSubmitting || cartHasStockProblems}>
                  {cartHasStockProblems ? "Исправьте корзину" : (orderSubmitting ? "Оформляем..." : "Оформить заказ")}
                </button>
                <button type="button" className="secondary" onClick={clearCart} disabled={loading}>
                  <Trash2 size={18} />
                  Очистить корзину
                </button>
              </div>
            </>
          )}
        </section>
      )}

      {screen === "bonus" && (
        <section className="section bonusPage">
          <div className="sectionHead">
            <h2>BONUS</h2>
            <span>{bonus.balance || 0}</span>
          </div>

          <div className="bonusHero">
            <div>
              <small>SYNDICATE BONUS</small>
              <strong>{bonus.balance || 0} баллов</strong>
              <span>1 балл = 1 ₽</span>
            </div>
            <Gift size={42} />
          </div>

          <div className="bonusRules">
            <h3>Система кэшбэка</h3>
            <p>После каждой покупки начисляется 2% от стоимости товаров без учёта доставки и доплаты за дату.</p>
            <p>Баллами можно оплатить до 40% стоимости заказа.</p>
            <p>Баллы бессрочные, суммируются и могут использоваться частями.</p>
          </div>

          <div className="bonusRules">
            <h3>Реферальная система</h3>
            <p>Пригласи друга. После его первой покупки тебе начислятся бонусы.</p>
            <p>100 баллов за заказ до 2 000 ₽.</p>
            <p>150 баллов за заказ от 2 000 ₽.</p>

            <div className="referralBox">
              <span>Твой код</span>
              <b>{bonus.referral_code}</b>
              <button type="button" onClick={copyReferralLink}>Скопировать ссылку</button>
            </div>
          </div>

          <div className="bonusHistory">
            <h3>История бонусов</h3>
            {bonus.transactions?.length ? (
              bonus.transactions.map((tx, index) => (
                <div className="bonusTx" key={`${tx.created_at}-${index}`}>
                  <div>
                    <b>{bonusTxTitle(tx.type)}</b>
                    <small>{tx.note || tx.created_at}</small>
                  </div>
                  <strong className={Number(tx.amount) >= 0 ? "plus" : "minus"}>
                    {Number(tx.amount) >= 0 ? "+" : ""}{tx.amount}
                  </strong>
                </div>
              ))
            ) : (
              <p className="muted">Истории пока нет</p>
            )}
          </div>
        </section>
      )}

      {screen === "orders" && (
        <section className="section">
          <div className="sectionHead">
            <h2>Мои заказы</h2>
            <span>{orders.length}</span>
          </div>

          {orders.length === 0 ? (
            <p className="muted">Заказов пока нет</p>
          ) : (
            <div className="ordersList">
              {orders.map((o) => (
                <div className="orderCard" key={o.id}>
                  <div>
                    <b>Заказ №{o.id}</b>
                    <small>{o.created_at}</small>
                  </div>
                  <div>
                    <span>{statusRu(o.status)}</span>
                    <strong>{o.total} ₽</strong>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {!selectedProduct && (
      <nav className="bottomNav">
        <button type="button" className={screen === "categories" || screen === "products" ? "active" : ""} onClick={() => setScreen("categories")}>
          <ShoppingBag size={22} />
          <span>Каталог</span>
        </button>
        <button type="button" className={screen === "cart" ? "active" : ""} onClick={openCart}>
          <ShoppingCart size={22} />
          <span>Корзина</span>
          {cart.count > 0 && <em>{cart.count}</em>}
        </button>
        <button type="button" className={screen === "orders" ? "active" : ""} onClick={openOrders}>
          <Package size={22} />
          <span>Заказы</span>
        </button>
        <button type="button" className={screen === "bonus" ? "active" : ""} onClick={openBonus}>
          <Gift size={22} />
          <span>BONUS</span>
        </button>
        <a href="https://t.me/guapsyndicate" target="_blank">
          <MessageSquare size={22} />
          <span>Поддержка</span>
        </a>
      </nav>
      )}

      <ProductModal
        product={selectedProduct}
        onClose={() => setSelectedProduct(null)}
        onAdd={async (productId, variant, quantity) => {
          await addToCart(productId, variant, quantity);
          setSelectedProduct(null);
        }}
      />
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
