let qr;

function generateQR() {
  const text = document.getElementById('qr-text').value.trim();
  const size = parseInt(document.getElementById('qr-size').value) || 256;
  const color = document.getElementById('qr-color').value;
  const qrContainer = document.getElementById('qrcode');

  if (!text) return alert("Por favor, introduce un texto o enlace.");

  // Limpiar QR anterior
  qrContainer.innerHTML = "";

  // Crear nuevo QR
  qr = new QRCode(qrContainer, {
    text: text,
    width: size,
    height: size,
    colorDark: color,
    colorLight: "#ffffff",
    correctLevel: QRCode.CorrectLevel.H
  });

  // Mostrar enlace debajo
  const qrLink = document.getElementById('qr-link');
  qrLink.textContent = text;
  qrLink.classList.remove('hidden');
}

function downloadQR() {
  const qrCanvas = document.querySelector('#qrcode canvas');
  const subText = document.getElementById('qr-subtext').value;

  if (!qrCanvas) {
    alert("Genera primero el código QR.");
    return;
  }

  const qrSize = qrCanvas.width;
  const spacing = 20;
  const textFontSize = 18;
  const textHeight = subText ? spacing + textFontSize + 10 : 0;

  // Crear canvas final con espacio para QR + texto
  const finalCanvas = document.createElement('canvas');
  finalCanvas.width = qrSize;
  finalCanvas.height = qrSize + textHeight;

  const ctx = finalCanvas.getContext('2d');
  ctx.fillStyle = "#FFFFFF";
  ctx.fillRect(0, 0, finalCanvas.width, finalCanvas.height);

  // Dibujar QR
  ctx.drawImage(qrCanvas, 0, 0);

  // Dibujar texto si existe
  if (subText) {
    ctx.fillStyle = "#000000";
    ctx.font = `${textFontSize}px Arial`;
    ctx.textAlign = "center";
    ctx.fillText(subText, qrSize / 2, qrSize + spacing + textFontSize / 2);
  }

  // Descargar
  const link = document.createElement('a');
  link.download = 'codigo_qr.png';
  link.href = finalCanvas.toDataURL('image/png');
  link.click();
}
