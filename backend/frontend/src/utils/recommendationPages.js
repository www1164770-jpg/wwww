export function recommendationPage(pool,index,size) {
  const width=Math.max(1,Math.min(16,Math.trunc(size)||16));
  const page=Math.max(0,Math.trunc(index)||0);
  return pool.slice(page*width,(page+1)*width);
}
