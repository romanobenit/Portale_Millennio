module.exports = {
  // Escludi dalla misurazione i file di interfaccia puri (nessuna implementazione)
  skipFiles: [],

  // Mostra output dettagliato delle righe non coperte
  istanbulReporter: ["text", "lcov", "json"],

  // Nota: _increaseBalance (override obbligatorio ERC721+ERC721Enumerable) e
  // i branch interni del virtual override chain di OZ v5 risultano non coperti
  // per un limite noto di solidity-coverage con le call interne.
  // La logica è verificata indirettamente da tutti i test di mint e balanceOf.
};
