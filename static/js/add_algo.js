function addLeg() {
    const legContainer = document.getElementById("legs-container");

    const newLeg = document.createElement("div");
    newLeg.classList.add("box", "mt-3");
    newLeg.innerHTML = `
        <div class="field">
            <label class="label">Instrument Name</label>
            <div class="control">
                <input class="input" type="text" name="instrument_name[]" placeholder="e.g. NIFTY">
            </div>
        </div>

        <div class="field">
            <label class="label">Expiry Date</label>
            <div class="control">
                <input class="input" type="text" name="expiry_date[]" placeholder="e.g. 27-JUN-2025">
            </div>
        </div>

        <div class="field">
            <label class="label">Strike Price</label>
            <div class="control">
                <input class="input" type="text" name="strike_price[]" placeholder="e.g. 19200">
            </div>
        </div>

        <div class="field">
            <label class="label">Option Type</label>
            <div class="control">
                <div class="select">
                    <select name="option_type[]">
                        <option value="CE">Call (CE)</option>
                        <option value="PE">Put (PE)</option>
                    </select>
                </div>
            </div>
        </div>

        <div class="field">
            <label class="label">Order Type</label>
            <div class="control">
                <div class="select">
                    <select name="order_type[]">
                        <option value="BUY">Buy</option>
                        <option value="SELL">Sell</option>
                    </select>
                </div>
            </div>
        </div>
    `;

    legContainer.appendChild(newLeg);
}
