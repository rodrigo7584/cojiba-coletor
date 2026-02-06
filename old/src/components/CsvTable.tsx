"use client";

interface CsvRow {
  nome: string;
  ean: string;
  codFamilia: string;
}

export default function CsvTable({ data }: { data: CsvRow[] }) {
  if (!data || data.length === 0) return <p>Nenhum dado carregado.</p>;

  return (
    <table className="border border-gray-400 w-full text-left">
      <thead>
        <tr>
          <th className="border px-4 py-2">Nome</th>
          <th className="border px-4 py-2">EAN</th>
          <th className="border px-4 py-2">Código Família</th>
        </tr>
      </thead>
      <tbody>
        {data.map((row, index) => (
          <tr key={index}>
            <td className="border px-4 py-2">{index}-{row.nome}</td>
            <td className="border px-4 py-2">{row.ean}</td>
            <td className="border px-4 py-2">{row.codFamilia}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
