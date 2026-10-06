// Injected into every page/frame before any site script runs.
// Exposes an EIP-1193 provider (window.ethereum) + EIP-6963 announcement.
// Every request is forwarded to Python through the `__agentWalletRequest`
// binding, where the spending policy and Telegram approvals live.
// Nothing in this file can sign on its own - the key never touches the page.
(() => {
  if (window.__agentWalletInstalled) return;
  window.__agentWalletInstalled = true;

  const listeners = {};
  let chainIdHex = "__CHAIN_ID_HEX__";
  let accounts = [];

  const emit = (event, payload) => {
    (listeners[event] || []).slice().forEach((fn) => {
      try { fn(payload); } catch (e) { console.error(e); }
    });
  };

  // Called from Python when the chain changes (wallet_switchEthereumChain).
  window.__agentWalletEmit = (event, payload) => {
    if (event === "chainChanged") chainIdHex = payload;
    if (event === "accountsChanged") accounts = payload;
    emit(event, payload);
  };

  const request = async ({ method, params } = {}) => {
    if (!method) throw Object.assign(new Error("Invalid request"), { code: -32600 });
    if (typeof window.__agentWalletRequest !== "function") {
      throw Object.assign(new Error("Wallet bridge unavailable"), { code: 4900 });
    }
    const raw = await window.__agentWalletRequest(JSON.stringify({ method, params: params || [] }));
    const res = JSON.parse(raw);
    if (res.error) {
      const err = new Error(res.error.message || "Request failed");
      err.code = res.error.code ?? 4001;
      throw err;
    }
    if (method === "eth_requestAccounts" || method === "eth_accounts") {
      const changed = JSON.stringify(accounts) !== JSON.stringify(res.result);
      accounts = res.result;
      if (changed && accounts.length) {
        emit("connect", { chainId: chainIdHex });
        emit("accountsChanged", accounts);
      }
    }
    if (method === "eth_chainId") chainIdHex = res.result;
    return res.result;
  };

  const provider = {
    isMetaMask: true, // many dApps only show a button for "MetaMask"
    isAgentWallet: true,
    _metamask: { isUnlocked: async () => true },
    get chainId() { return chainIdHex; },
    get networkVersion() { return String(parseInt(chainIdHex, 16)); },
    get selectedAddress() { return accounts[0] || null; },
    isConnected: () => true,
    request,
    enable: () => request({ method: "eth_requestAccounts" }),
    send: (methodOrPayload, paramsOrCallback) => {
      if (typeof methodOrPayload === "string") {
        return request({ method: methodOrPayload, params: paramsOrCallback });
      }
      if (typeof paramsOrCallback === "function") {
        return provider.sendAsync(methodOrPayload, paramsOrCallback);
      }
      return request(methodOrPayload);
    },
    sendAsync: (payload, cb) => {
      request(payload).then(
        (result) => cb(null, { id: payload.id, jsonrpc: "2.0", result }),
        (error) => cb(error, null),
      );
    },
    on: (event, fn) => { (listeners[event] = listeners[event] || []).push(fn); return provider; },
    once: (event, fn) => {
      const wrap = (p) => { provider.removeListener(event, wrap); fn(p); };
      return provider.on(event, wrap);
    },
    removeListener: (event, fn) => {
      listeners[event] = (listeners[event] || []).filter((f) => f !== fn);
      return provider;
    },
    off: (event, fn) => provider.removeListener(event, fn),
    removeAllListeners: (event) => { if (event) delete listeners[event]; return provider; },
  };

  try {
    Object.defineProperty(window, "ethereum", { value: provider, writable: false, configurable: false });
  } catch (e) {
    window.ethereum = provider;
  }
  window.dispatchEvent(new Event("ethereum#initialized"));

  // EIP-6963 multi-wallet discovery (RainbowKit, wagmi, Web3Modal, Dynamic...)
  const info = Object.freeze({
    uuid: "7f1d3c2a-6b2e-4c39-9d7e-agentwallet0",
    name: "Agent Wallet",
    icon: "data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAzMiAzMic+PHJlY3Qgd2lkdGg9JzMyJyBoZWlnaHQ9JzMyJyByeD0nOCcgZmlsbD0nIzAwNTJGRicvPjxwYXRoIGQ9J004IDE2bDUgNSAxMS0xMScgc3Ryb2tlPSd3aGl0ZScgc3Ryb2tlLXdpZHRoPSczJyBmaWxsPSdub25lJy8+PC9zdmc+",
    rdns: "app.agentwallet",
  });
  const announce = () => window.dispatchEvent(
    new CustomEvent("eip6963:announceProvider", { detail: Object.freeze({ info, provider }) }),
  );
  window.addEventListener("eip6963:requestProvider", announce);
  announce();
})();
