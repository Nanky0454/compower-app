<script setup>
// No script logic needed for static content
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold mb-6">
      Resumen de Novedades y Funciones Implementadas
    </h1>

    <div class="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Gestión de Catálogo</CardTitle>
        </CardHeader>
        <CardContent>
          <ul class="list-disc pl-6 space-y-2">
            <li>
              <strong>Eliminación de Categorías:</strong> Se ha añadido un botón para eliminar categorías en la vista de "Ajustes y Carga > Categorías".
            </li>
            <li>
              <strong>Instrucciones de Importación:</strong> Ahora se muestran indicaciones claras sobre las columnas requeridas y opcionales para la importación de productos desde un archivo Excel.
            </li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Gestión de Inventario y Reportes</CardTitle>
        </CardHeader>
        <CardContent>
          <ul class="list-disc pl-6 space-y-2">
            <li>
              <strong>Columna "Ubicación":</strong> El reporte de stock ahora incluye la columna "Ubicación" para una mejor trazabilidad.
            </li>
            <li>
              <strong>Generación de Etiquetas:</strong> Se ha incorporado un botón "Generar Etiquetas" que crea un PDF con el SKU, nombre y logo del producto, listo para imprimir en formato A4.
            </li>
            <li>
              <strong>Nuevos Filtros:</strong> El reporte de stock ahora cuenta con un filtro funcional por "Ubicación" y se ha mejorado el filtro por "Categoría", que ahora muestra los checks de selección.
            </li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Impresión</CardTitle>
        </CardHeader>
        <CardContent>
          <ul class="list-disc pl-6 space-y-2">
            <li>
              <strong>Formato de Impresión Vertical:</strong> El reporte de stock se ha ajustado para imprimirse por defecto en formato A4 vertical.
            </li>
            <li>
              <strong>Optimización de Escala:</strong> Se han aplicado estilos más agresivos para que la tabla del reporte quepa mejor en la hoja, reduciendo la necesidad de ajustar la escala manualmente al 50%.
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
