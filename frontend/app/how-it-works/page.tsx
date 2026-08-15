import { Card } from "@/components/ui";

export default function HowItWorksPage() {
  return (
    <>
      <header className="page-title">
        <div>
          <span className="eyebrow">Always-open prediction markets</span>
          <h1>How LMSR works</h1>
          <p>
            BullyMarket uses a Logarithmic Market Scoring Rule. The house quotes every
            trade, so you can buy shares without waiting for another person to match it.
          </p>
        </div>
      </header>

      <div className="explanation-grid">
        <Card className="card-pad explanation-lead">
          <span className="eyebrow">The short version</span>
          <h2>Price is probability</h2>
          <p>
            YES and NO begin at 50%. Buying YES issues more YES shares and raises its
            price; buying NO does the opposite. If your side wins, each share pays 1
            point. If it loses, it pays 0.
          </p>
          <div className="lmsr-example">
            <div><strong>42%</strong><span>YES price</span></div>
            <div><strong>58%</strong><span>NO price</span></div>
          </div>
        </Card>

        <Card className="card-pad">
          <span className="eyebrow">Market state</span>
          <h2>Only three values drive the price</h2>
          <p>
            <code>q_yes</code> and <code>q_no</code> are the net shares issued on each
            side. <code>b</code> is fixed when the market is created and controls depth.
            A larger <code>b</code> means each purchase moves the odds less.
          </p>
        </Card>

        <Card className="card-pad formula-card">
          <span className="eyebrow">Cost function</span>
          <h2>What a purchase costs</h2>
          <pre>C(q_yes, q_no) = b × ln(exp(q_yes / b) + exp(q_no / b))</pre>
          <p>
            Your quote is the difference between the cost function after the purchase
            and before it. That is why a larger order has visible price impact.
          </p>
        </Card>

        <Card className="card-pad formula-card">
          <span className="eyebrow">Live odds</span>
          <h2>How the displayed price is calculated</h2>
          <pre>P_yes = exp(q_yes / b) / (exp(q_yes / b) + exp(q_no / b))</pre>
          <p>
            YES and NO prices always add to 100%. The server calculates all quotes; the
            browser never guesses or reimplements the formula.
          </p>
        </Card>

        <Card className="card-pad">
          <span className="eyebrow">House risk</span>
          <h2>The loss is bounded</h2>
          <p>
            The worst possible house loss for a binary market is <code>b × ln(2)</code>.
            BullyMarket records that reserve at creation and separately audits every
            trade, payout, refund, correction, and final house profit or loss.
          </p>
        </Card>

        <Card className="card-pad">
          <span className="eyebrow">One important detail</span>
          <h2>Early conviction gets a better average price</h2>
          <p>
            As a side is bought, its next share becomes more expensive. Early buyers
            therefore receive a better average price when their prediction later becomes
            popular. The confirmation quote shows both your average price and the odds
            after your purchase.
          </p>
        </Card>
      </div>
    </>
  );
}
