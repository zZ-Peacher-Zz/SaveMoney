// Preview the square image through a circular window, matching the saved avatar.
async function openAvatarCrop(file) {
  const url = URL.createObjectURL(file);
  const image = new Image();
  try {
    image.src = url;
    await image.decode();
    if (image.naturalWidth * image.naturalHeight > 16000000) {
      throw new Error("Ảnh quá lớn, vui lòng chọn ảnh tối đa 16 megapixel");
    }

    return await new Promise(resolve => {
      const dialog = document.getElementById("avatarDialog");
      const canvas = document.getElementById("avatarCropCanvas");
      const zoom = document.getElementById("avatarZoom");
      const save = document.getElementById("saveAvatarCrop");
      const ctx = canvas.getContext("2d");
      const events = new AbortController();
      const options = {signal: events.signal};
      const size = canvas.width;
      const baseScale = Math.max(size / image.naturalWidth, size / image.naturalHeight);
      let scale = baseScale;
      let x = (size - image.naturalWidth * scale) / 2;
      let y = (size - image.naturalHeight * scale) / 2;
      let drag = null;
      let result = null;
      zoom.value = "1";
      save.disabled = false;

      function draw() {
        x = Math.min(0, Math.max(size - image.naturalWidth * scale, x));
        y = Math.min(0, Math.max(size - image.naturalHeight * scale, y));
        ctx.clearRect(0, 0, size, size);
        ctx.drawImage(image, x, y, image.naturalWidth * scale, image.naturalHeight * scale);
      }

      zoom.addEventListener("input", () => {
        const next = baseScale * Number(zoom.value);
        x = size / 2 - (size / 2 - x) * next / scale;
        y = size / 2 - (size / 2 - y) * next / scale;
        scale = next;
        draw();
      }, options);

      canvas.addEventListener("pointerdown", event => {
        if (!event.isPrimary || event.button !== 0) return;
        canvas.focus();
        canvas.setPointerCapture(event.pointerId);
        drag = {id: event.pointerId, x: event.clientX, y: event.clientY};
      }, options);
      canvas.addEventListener("pointermove", event => {
        if (!drag || drag.id !== event.pointerId) return;
        const ratio = size / canvas.getBoundingClientRect().width;
        x += (event.clientX - drag.x) * ratio;
        y += (event.clientY - drag.y) * ratio;
        drag.x = event.clientX;
        drag.y = event.clientY;
        draw();
      }, options);
      for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) {
        canvas.addEventListener(name, () => { drag = null; }, options);
      }
      canvas.addEventListener("keydown", event => {
        const step = event.shiftKey ? 20 : 5;
        const movement = {ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step]}[event.key];
        if (!movement) return;
        event.preventDefault();
        x += movement[0];
        y += movement[1];
        draw();
      }, options);

      document.getElementById("cancelAvatarCrop").addEventListener("click", () => dialog.close(), options);
      save.addEventListener("click", () => {
        save.disabled = true;
        canvas.toBlob(blob => {
          if (!dialog.open) return;
          result = blob;
          dialog.close();
        }, "image/png");
      }, options);
      dialog.addEventListener("close", () => {
        events.abort();
        ctx.clearRect(0, 0, size, size);
        resolve(result);
      }, {once: true});
      draw();
      dialog.showModal();
      canvas.focus();
    });
  } finally {
    URL.revokeObjectURL(url);
  }
}
