<script>
export default {
  data() {
    return {
      tokenValue: 0.1
    }
  }
}
</script>

<template>
  <div class="redefi-panel">
    <div class="from-chain">
      <div>from chain</div>
      <div class="image">
        <img src="../assets/Ethereum.svg" alt="Ethereum" />
        <div class="selector network">testnet</div>
      </div>
    </div>
    <div class="delimiter">
      <div class="cube"><div class="arrow">&rarr;</div></div>
    </div>
    <div class="to-chain">
      <div>to chain</div>
      <div class="image">
        <img src="../assets/ReDeFi.svg" alt="ReDeFi" />
        <div class="selector network">L1 testnet</div>
      </div>
    </div>
    <div class="token-selector selector">
      <input type="number" v-model="tokenValue" step="0.01" min="0.01" max="1000000" />
    </div>
    <div class="submit-button">
      <div class="button">submit</div>
    </div>
  </div>
</template>

<style lang="less">
  .redefi-panel {
    max-width: 800px;
    margin: 0 auto;
    display: grid;
    grid-template: "from delimiter to" "token-selector token-selector token-selector" "submit-button submit-button submit-button";
    grid-template-columns: 1fr auto 1fr;
    border-top: 3px solid var(--color);
    background: rgb(38, 41, 46);
    grid-gap: var(--indent);
    padding: var(--margin);
    text-transform: uppercase;
    font-weight: 600;

    .from-chain {
      grid-area: from;
    }
    .delimiter {
      grid-area: delimiter;
      align-self: center;

      .cube {
        background: var(--background);
        transform: rotate(45deg);
        width: 40px;
        height: 40px;
        display: block;

        .arrow {
          transform: rotate(-45deg);
          font-size: 24px;
          text-align: center;
        }
      }
    }
    .to-chain {
      grid-area: to;
    }
    .to-chain, .from-chain {
      text-align: center;

      .image {
        display: inline-block;
        position: relative;
        margin: var(--indent) auto;

        img {
          width: 128px;
          max-width: 128px;
          max-height: 128px;
        }

        .selector {
          position: relative;
          bottom: 20px;
          left: 0;
          border-radius: var(--font-size);
        }
      }
    }

    .token-selector {
      grid-area: token-selector;

      input {
        background: transparent;
        border: none;
        outline: 0;
        color: var(--color);
        font-size: 1.5em;
        font-family: var(--font-family);
        font-weight: 600;
        padding: var(--indent);
         width: 100%;
      }
    }

    .submit-button {
      grid-area: submit-button;

      .button {
        text-align: center;
        background: rgb(253, 2, 2);
        padding: 6px;
      }
    }

    .selector {
      background: rgb(34, 46, 58);
    }
  }
</style>
