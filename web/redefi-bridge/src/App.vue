<script setup>
import Header from './components/Header.vue'
import BridgePanel from './components/BridgePanel.vue'
</script>

<template>
  <header>
    <Header />
  </header>

  <main>
    <div class="bridge-title">
      <div class="main-title">ReDeFi Bridge</div>
      <div>Bridge your tokens with no additional fees</div>
    </div>
    <BridgePanel />
  </main>
</template>

<style lang="less">
  .bridge-title {
    font-weight: 600;
    text-align: center;
    margin-top: 72px;
    margin-bottom: 36px;

    .main-title {
      line-height: 1;
      font-size: 2.5em;
    }
  }

</style>
