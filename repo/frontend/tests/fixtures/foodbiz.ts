export const restaurant = {
  restaurantId: "rst_001",
  name: "Bella Vista Kitchen",
  timezone: "America/Chicago",
  currency: "USD",
  createdAt: "2026-04-08T12:00:00Z",
};

export const menuResponse = {
  menuId: "men_001",
  restaurantId: "rst_001",
  menuVersion: 1,
  updatedAt: "2026-04-08T12:00:00Z",
  categories: [
    {
      categoryId: "cat_italian",
      name: "Italian",
      categoryKind: "FOOD",
      cuisineOrFamily: "ITALIAN",
    },
    {
      categoryId: "cat_non_alcoholic",
      name: "Non-Alcoholic",
      categoryKind: "DRINK",
      cuisineOrFamily: "NON_ALCOHOLIC",
    },
  ],
  items: [
    {
      itemId: "itm_001",
      name: "Margherita Pizza",
      description: "Fresh mozzarella, basil, and tomato sauce.",
      priceMoney: { amountCents: 1450, currency: "USD" },
      isAvailable: true,
      categoryId: "cat_italian",
      allowedModifiers: [
        {
          code: "crust",
          label: "Crust",
          kind: "choice",
          options: ["regular", "thin", "gluten_free"],
        },
      ],
    },
    {
      itemId: "itm_021",
      name: "Lemonade",
      description: "House-made lemonade.",
      priceMoney: { amountCents: 420, currency: "USD" },
      isAvailable: true,
      categoryId: "cat_non_alcoholic",
      allowedModifiers: [
        {
          code: "sparkling",
          label: "Sparkling",
          kind: "toggle",
        },
      ],
    },
  ],
};

export const locationsResponse = {
  locations: [
    {
      locationId: "loc_tbl_001",
      restaurantId: "rst_001",
      type: "TABLE",
      name: "Table 1",
      displayLabel: "Table 1",
      capacity: 4,
      zone: "Main Dining",
      isActive: true,
      createdAt: "2026-04-08T12:00:00Z",
      sessionStatus: "OPEN",
      activeSessionId: "ses_001",
      lastSessionOpenedAt: "2026-04-08T12:00:00Z",
    },
    {
      locationId: "loc_tbl_002",
      restaurantId: "rst_001",
      type: "TABLE",
      name: "Table 2",
      displayLabel: "Table 2",
      capacity: 4,
      zone: "Main Dining",
      isActive: true,
      createdAt: "2026-04-08T12:00:00Z",
      sessionStatus: "CLOSED",
      activeSessionId: null,
      lastSessionOpenedAt: null,
    },
    {
      locationId: "loc_bar_001",
      restaurantId: "rst_001",
      type: "BAR_SEAT",
      name: "Bar Seat 1",
      displayLabel: "Bar Seat 1",
      capacity: 1,
      zone: "Bar",
      isActive: true,
      createdAt: "2026-04-08T12:00:00Z",
      sessionStatus: null,
      activeSessionId: null,
      lastSessionOpenedAt: null,
    },
    {
      locationId: "loc_online_pickup",
      restaurantId: "rst_001",
      type: "ONLINE_PICKUP",
      name: "Pickup",
      displayLabel: "Pickup Counter",
      capacity: null,
      zone: "Off Premise",
      isActive: true,
      createdAt: "2026-04-08T12:00:00Z",
      sessionStatus: null,
      activeSessionId: null,
      lastSessionOpenedAt: null,
    },
    {
      locationId: "loc_online_delivery",
      restaurantId: "rst_001",
      type: "ONLINE_DELIVERY",
      name: "Delivery",
      displayLabel: "Delivery Dispatch",
      capacity: null,
      zone: "Off Premise",
      isActive: true,
      createdAt: "2026-04-08T12:00:00Z",
      sessionStatus: null,
      activeSessionId: null,
      lastSessionOpenedAt: null,
    },
  ],
};

export const emptyTableOrdersResponse = {
  orders: [],
  nextCursor: null,
};

export const createdPickupOrder = {
  orderId: "ord_pickup_001",
  restaurantId: "rst_001",
  locationId: "loc_online_pickup",
  tableId: null,
  sessionId: null,
  source: "ONLINE_PICKUP",
  status: "PLACED",
  lines: [
    {
      lineId: "line_001",
      itemId: "itm_001",
      name: "Margherita Pizza",
      quantity: 1,
      unitPrice: { amountCents: 1450, currency: "USD" },
      lineTotal: { amountCents: 1450, currency: "USD" },
      notes: null,
      modifiers: [{ code: "crust", label: "Crust", value: "thin" }],
    },
  ],
  total: { amountCents: 1450, currency: "USD" },
  createdAt: "2026-04-08T12:30:00Z",
  updatedAt: "2026-04-08T12:30:00Z",
};

export const createdDeliveryOrder = {
  ...createdPickupOrder,
  orderId: "ord_delivery_001",
  locationId: "loc_online_delivery",
  source: "ONLINE_DELIVERY",
};

export const createdDineInOrder = {
  ...createdPickupOrder,
  orderId: "ord_dine_in_001",
  locationId: "loc_tbl_001",
  tableId: "tbl_001",
  sessionId: "ses_001",
  source: "WEB_DINE_IN",
};

export const readyServiceOrder = {
  ...createdDineInOrder,
  orderId: "ord_ready_001",
  status: "READY",
};

export const placedKitchenOrder = {
  ...createdPickupOrder,
  orderId: "ord_kitchen_placed_001",
  locationId: "loc_tbl_001",
  tableId: "tbl_001",
  sessionId: "ses_001",
  source: "WEB_DINE_IN",
  status: "PLACED",
};

export const acceptedKitchenOrder = {
  ...placedKitchenOrder,
  orderId: "ord_kitchen_accepted_001",
  status: "ACCEPTED",
};

export const tableRegistryResponse = {
  tables: [
    {
      tableId: "tbl_001",
      restaurantId: "rst_001",
      status: "OPEN",
      openedAt: "2026-04-08T12:00:00Z",
      closedAt: null,
      lastOrderAt: "2026-04-08T12:25:00Z",
      totals: { amountCents: 1450, currency: "USD" },
      counts: {
        ordersTotal: 1,
        placed: 0,
        accepted: 0,
        ready: 1,
        served: 0,
        settled: 0,
      },
    },
    {
      tableId: "tbl_002",
      restaurantId: "rst_001",
      status: "CLOSED",
      openedAt: null,
      closedAt: "2026-04-08T11:00:00Z",
      lastOrderAt: null,
      totals: { amountCents: 0, currency: "USD" },
      counts: {
        ordersTotal: 0,
        placed: 0,
        accepted: 0,
        ready: 0,
        served: 0,
        settled: 0,
      },
    },
  ],
  nextCursor: null,
};

export const tableSummaryResponse = {
  tableId: "tbl_001",
  restaurantId: "rst_001",
  status: "OPEN",
  openedAt: "2026-04-08T12:00:00Z",
  closedAt: null,
  totals: { amountCents: 1450, currency: "USD" },
  counts: {
    ordersTotal: 1,
    placed: 0,
    accepted: 0,
    ready: 1,
    served: 0,
    settled: 0,
  },
  lastOrderAt: "2026-04-08T12:25:00Z",
};
