import Papa from 'papaparse';

export function parseCsv(file, callback) {
  Papa.parse(file, {
    delimiter: ";",
    skipEmptyLines: true,
    complete: function (results) {
      const data = results.data
        .map((row) => {
          let nomeOriginal = row[0] || '';
          let nomeSanitizado = nomeOriginal.split(":")[0].trim();
          let ean = row[1]?.trim() || '';
          let codFamilia = row[2]?.trim() || '';

          return {
            nome: nomeSanitizado,
            ean,
            codFamilia,
          };
        })
        .filter((item) => (item.ean.length === 8 || item.ean.length === 13))
        .reduce((acc, curr) => {
          const exists = acc.find(item => item.codFamilia === curr.codFamilia);
          if (!exists) acc.push(curr);
          return acc;
        }, []);

      callback(data);
    },
  });
}
