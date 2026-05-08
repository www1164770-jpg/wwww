<template>
  <div id="app-root">
    <router-view></router-view> 
  </div>
</template>

<style>
body { margin: 0; padding: 0; font-family: sans-serif; }
/* 强制显示垂直滚动条，彻底杜绝因滚动条时隐时现导致的页面左右晃动 */
html {
  overflow-y: scroll; 
}
</style>