import React from 'react';
import { Box, Typography, Container, Paper } from '@mui/material';
import SEO from '../components/SEO';

const TermsOfServicePage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <SEO
        title="Terms of Service"
        description="The terms that govern your use of GetSTAM."
        canonicalPath="/terms-of-service"
      />
      <Paper elevation={2} sx={{ p: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ color: '#1976d2', fontWeight: 'bold' }}>
          Terms of Service
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Last updated: August 18, 2026
        </Typography>

        <Typography variant="body1" paragraph>
          These Terms of Service ("Terms") govern your access to and use of GetSTAM (the "Service"), operated by
          GetStam ("Company", "We", "Us", "Our"). By creating an account or otherwise using the Service, You agree
          to be bound by these Terms. If You do not agree, do not use the Service.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          The Service
        </Typography>
        <Typography variant="body1" paragraph>
          GetSTAM provides sports statistics, historical trends, and related information for entertainment and
          informational purposes only. Nothing on the Service constitutes betting, financial, or professional
          advice, and We make no guarantee of the accuracy, completeness, or timeliness of any data, odds, or
          trend shown. You are solely responsible for any decisions You make based on information from the
          Service.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Accounts
        </Typography>
        <Typography variant="body1" paragraph>
          You must provide accurate information when creating an account and are responsible for maintaining the
          confidentiality of Your login credentials and for all activity under Your account. Notify Us immediately
          of any unauthorized use.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Subscriptions and Billing
        </Typography>
        <Box component="ul" sx={{ pl: 3, mb: 3 }}>
          <Box component="li" sx={{ mb: 1 }}>
            <Typography variant="body1">
              <strong>Pro plan.</strong> Certain features require a paid "Pro" subscription, billed monthly through
              Our payment processor, Stripe. Pricing is shown at checkout before You subscribe.
            </Typography>
          </Box>
          <Box component="li" sx={{ mb: 1 }}>
            <Typography variant="body1">
              <strong>Free trial.</strong> New Pro subscriptions may include a free trial period. Unless You cancel
              before the trial ends, You will automatically be charged the subscription price and Your subscription
              will continue on a recurring basis.
            </Typography>
          </Box>
          <Box component="li" sx={{ mb: 1 }}>
            <Typography variant="body1">
              <strong>Auto-renewal and cancellation.</strong> Subscriptions renew automatically each billing period
              until canceled. You can cancel at any time from the "Manage Billing" option in Your account menu,
              which opens Our payment processor's self-service billing portal. Cancellation takes effect at the end
              of the current billing period; We do not provide partial-period refunds except where required by law.
            </Typography>
          </Box>
          <Box component="li" sx={{ mb: 1 }}>
            <Typography variant="body1">
              <strong>Access codes.</strong> Promotional or complimentary access codes may grant Pro access on
              terms We specify at the time they are issued and may be modified or revoked at Our discretion.
            </Typography>
          </Box>
        </Box>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Acceptable Use
        </Typography>
        <Typography variant="body1" paragraph>
          You agree not to misuse the Service, including by attempting to access it through automated means outside
          any API We offer, interfering with its operation, or using it for any unlawful purpose.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Disclaimers
        </Typography>
        <Typography variant="body1" paragraph>
          The Service is provided "as is" and "as available" without warranties of any kind, express or implied.
          GetSTAM does not offer real-money gambling or betting services. Sports data, odds, and trends are for
          entertainment purposes only and are not a guarantee of any outcome. Must be 18+ (or 21+ in some
          jurisdictions) to use the Service. Gamble responsibly — if you or someone you know has a gambling
          problem, visit NCPGambling.org or call 1-800-GAMBLER.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Data Accuracy and Third-Party Sources
        </Typography>
        <Typography variant="body1" paragraph>
          Scores, odds, lines, statistics, and other data shown on the Service are sourced from third-party
          providers We do not control. We maintain internal review processes intended to catch errors before data
          reaches the Service, but We cannot guarantee that any data is complete, current, or error-free. If a
          third-party source is delayed, incomplete, or incorrect, data on the Service may be delayed, incomplete,
          or incorrect as a result. You should independently verify any information — including odds and lines —
          with an official or licensed source before relying on it for any purpose. Use of the Service, and any
          reliance on data it displays, is entirely at Your own risk.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          No Liability for Betting or Wagering Decisions
        </Typography>
        <Typography variant="body1" paragraph>
          GetSTAM is an informational and entertainment service only. We do not place bets, accept wagers, or act
          as a sportsbook, and nothing on the Service is betting or financial advice. Any decision to place a bet
          or wager, with any third party, based in whole or in part on information from the Service, is made
          solely at Your own discretion and risk. The Company is not liable for any losses, damages, or harm —
          financial or otherwise — resulting from bets or wagers You place, whether or not the data, odds, or
          trends You relied on were accurate, complete, or up to date at the time.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Limitation of Liability
        </Typography>
        <Typography variant="body1" paragraph>
          To the maximum extent permitted by law, the Company and its officers, employees, and agents shall not be
          liable for any indirect, incidental, special, consequential, or punitive damages, or any loss of
          profits, revenue, or funds wagered, arising from or related to Your use of the Service — including
          decisions made in reliance on data, odds, or trends We provide, and including where such data, odds, or
          trends are inaccurate, delayed, or incomplete due to errors from Us or from a third-party source. To the
          maximum extent permitted by law, the Company's total liability to You for any claim arising from the
          Service shall not exceed the greater of (a) the amount You paid Us in the twelve (12) months before the
          claim arose, or (b) one hundred U.S. dollars ($100).
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Termination
        </Typography>
        <Typography variant="body1" paragraph>
          We may suspend or terminate Your access to the Service at any time for conduct that violates these Terms
          or is otherwise harmful to the Service or other users. You may stop using the Service and close Your
          account at any time.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Changes to These Terms
        </Typography>
        <Typography variant="body1" paragraph>
          We may update these Terms from time to time. We will post the revised Terms on this page and update the
          "Last updated" date. Continued use of the Service after changes take effect constitutes acceptance of
          the revised Terms.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Governing Law
        </Typography>
        <Typography variant="body1" paragraph>
          These Terms are governed by the laws of the State of Colorado, United States, without regard to conflict
          of law principles.
        </Typography>

        <Typography variant="h4" component="h2" gutterBottom sx={{ mt: 4, color: '#1976d2' }}>
          Contact Us
        </Typography>
        <Typography variant="body1" paragraph>
          If you have any questions about these Terms, You can contact us:
        </Typography>
        <Typography variant="body1" paragraph>
          By email: getstaminc@gmail.com
        </Typography>
      </Paper>
    </Container>
  );
};

export default TermsOfServicePage;
