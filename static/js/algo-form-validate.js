// static/js/algo-form-validate.js
(function (win, doc) {
  function initAlgoFormValidation(options = {}) {
    const {
      nameId = 'AlgoName',
      fundId = 'MinimumFund',
      nameHelpId = 'algoNameError',
      fundHelpId = 'fundError',
      gateBtnId = 'defineStrategyBtn',
      endpoint = '/check_algo_name/',
      excludeId = null,
      debounceMs = 300,
    } = options;

    const nameInput = doc.getElementById(nameId);
    const fundInput = doc.getElementById(fundId);
    const helpName  = doc.getElementById(nameHelpId);
    const helpFund  = doc.getElementById(fundHelpId);
    const gateBtn   = gateBtnId ? doc.getElementById(gateBtnId) : null;

    if (!nameInput) return; // not on this page

    let lastReq = 0;
    let nameOK  = false;

    function setDefineDisabled(disabled) { if (gateBtn) gateBtn.disabled = !!disabled; }
    function validateFund() {
      if (!fundInput || !helpFund) return true;
      const v = parseFloat(fundInput.value);
      const ok = !isNaN(v) && v > 0;
      helpFund.style.display = ok ? 'none' : 'block';
      return ok;
    }
    function updateGate() { if (gateBtn) setDefineDisabled(!(nameOK && validateFund())); }
    function showNameError(msg){ if(helpName){ helpName.textContent = msg; helpName.style.display='block'; } nameInput.classList.add('is-danger'); }
    function clearNameError(){ if(helpName){ helpName.style.display='none'; } nameInput.classList.remove('is-danger'); }

    function debounce(fn, ms){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; }

    const checkName = debounce(async function(){
      const raw = (nameInput.value || '').trim();
      if (!raw){ nameOK=false; showNameError('Algorithm name is required.'); updateGate(); return; }
      try{
        const reqId = ++lastReq;
        const url = new URL(endpoint, win.location.origin);
        url.searchParams.set('name', raw);
        if (excludeId != null && excludeId !== '') url.searchParams.set('exclude_id', excludeId);
        const resp = await fetch(url.toString(), { credentials: 'same-origin' });
        if (reqId !== lastReq) return;
        if (!resp.ok) throw new Error('network');
        const data = await resp.json();
        if (data.valid){ nameOK=true; clearNameError(); } else { nameOK=false; showNameError(data.message || 'Name is not available.'); }
      } catch(e){ nameOK=false; showNameError('Could not validate name. Check connection.'); }
      finally { updateGate(); }
    }, debounceMs);

    nameInput.addEventListener('input', checkName);
    if (fundInput) fundInput.addEventListener('input', ()=>{ validateFund(); updateGate(); });

    validateFund();
    if (gateBtn) setDefineDisabled(true);
    if (nameInput.value.trim()) checkName();
  }

  // ✅ export globally
  win.initAlgoFormValidation = initAlgoFormValidation;
})(window, document);
